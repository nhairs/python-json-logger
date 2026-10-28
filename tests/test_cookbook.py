"""Keep the cookbook's exception output in sync with its runnable example."""

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


def normalize_traceback(lines: list[str], code: str) -> list[str]:
    """Ignore frame details while retaining exception text and group structure."""
    source_lines = {line.strip() for line in code.splitlines() if line.strip()}
    normalized = []
    in_frame = False
    for line in lines:
        # Group frames have a vertical bar before the usual traceback indentation.
        content = line.strip().removeprefix("|").strip()
        if re.fullmatch(r'File ".*", line \d+, in .*', content):
            in_frame = True
            continue
        if in_frame and (content in source_lines or re.fullmatch(r"[~^]+", content)):
            continue
        in_frame = False
        normalized.append(line.strip())
    return normalized


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="Exception groups and notes require Python 3.11 or higher"
)
def test_exception_example() -> None:
    cookbook = (Path(__file__).resolve().parents[1] / "docs" / "cookbook.md").read_text(
        encoding="utf-8"
    )
    example = cookbook.split("## Logging exceptions, exception groups, and exception notes\n", 1)[
        1
    ].split("\n## ", 1)[0]
    code = re.search(r"```python\n(.*?)```", example, re.DOTALL)
    assert code is not None
    outputs = re.findall(r"```json\n(.*?)```", example, re.DOTALL)
    assert len(outputs) == 4

    result = subprocess.run(
        [sys.executable, "-c", code.group(1)],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    actual = [json.loads(line) for line in result.stderr.splitlines()]
    expected = [json.loads(output) for output in outputs]
    for record in actual + expected:
        if isinstance(record.get("exc_info"), list):
            record["exc_info"] = normalize_traceback(record["exc_info"], code.group(1))
    assert actual == expected
    return None
