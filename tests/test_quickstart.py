"""Keep the Quick Start's displayed JSON output in sync with its examples."""

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


@pytest.mark.parametrize("section", ["Default Fields", "Static Fields", "Field Precedence"])
def test_output_field_examples(section: str) -> None:
    quickstart = (Path(__file__).resolve().parents[1] / "docs" / "quickstart.md").read_text(
        encoding="utf-8"
    )
    setup = re.search(
        r"### Integrating with Python's logging framework.*?```python\n(.*?)```",
        quickstart,
        re.DOTALL,
    )
    assert setup is not None
    example = quickstart.split(f"#### {section}\n", 1)[1].split("\n###", 1)[0]
    code = re.search(r"```python\n(.*?)```", example, re.DOTALL)
    output = re.search(r"```json\n(.*?)```", example, re.DOTALL)
    assert code is not None
    assert output is not None

    result = subprocess.run(
        [sys.executable, "-c", setup.group(1) + "\n" + code.group(1)],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    actual = [json.loads(line) for line in result.stderr.splitlines()]
    expected = [json.loads(line) for line in output.group(1).splitlines()]
    assert actual == expected
    return None
