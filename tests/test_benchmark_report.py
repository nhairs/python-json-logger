"""Verify the standalone report's interpretation of benchmark result files."""

from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import pytest

REPORT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_report.py"


@pytest.fixture
def result_file(tmp_path: Path) -> Path:
    """Write a complete matrix with known times and relative speeds."""
    result = {
        "environment": {
            "python": "3.15.0",
            "revision": "abc123",
            "dirty": False,
            "dependencies": {"orjson": "1.0"},
        },
        "machine_info": {"system": "Linux", "release": "test", "machine": "x86_64"},
        "datetime": "2026-10-18T00:00:00",
        "benchmarks": [
            {
                "extra_info": {"layer": layer, "workload": workload, "backend": backend},
                "stats": {"median": 0.000002 if backend == "json" else 0.000001},
            }
            for layer, workload, backend in product(
                ("serialization", "formatting"),
                ("simple", "structured", "nested", "unicode", "rich", "exception"),
                ("json", "orjson", "msgspec"),
            )
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    return path


def test_report_update(result_file: Path, tmp_path: Path) -> None:
    """Tables show converted units and preserve prose across repeated regeneration."""
    page = tmp_path / "benchmarking.md"
    page.write_text(
        "Introduction\n<!-- benchmark-results:start -->\nold\n"
        "<!-- benchmark-results:end -->\nAfterword\n"
    )
    command = [sys.executable, str(REPORT), str(result_file), "--update", str(page)]
    subprocess.run(command, check=True, capture_output=True)
    first = page.read_text()
    assert "| serialization | simple | 2.000 | 1.000; 2.00× | 1.000; 2.00× |" in first
    assert first.startswith("Introduction\n")
    assert first.endswith("Afterword\n")
    subprocess.run(command, check=True, capture_output=True)
    assert page.read_text() == first
    return


@pytest.mark.parametrize("problem", ("missing", "duplicate", "zero", "nan"))
def test_report_rejects_invalid_matrix(result_file: Path, problem: str) -> None:
    """Incomplete, duplicated, and invalid timings must not become published tables."""
    result = json.loads(result_file.read_text())
    if problem == "missing":
        result["benchmarks"].pop()
    elif problem == "duplicate":
        result["benchmarks"].append(result["benchmarks"][0])
    else:
        result["benchmarks"][0]["stats"]["median"] = 0 if problem == "zero" else float("nan")
    result_file.write_text(json.dumps(result))
    completed = subprocess.run(
        [sys.executable, str(REPORT), str(result_file)], capture_output=True, text=True
    )
    assert completed.returncode != 0
    assert not completed.stdout
    return
