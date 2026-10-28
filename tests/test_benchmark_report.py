"""Verify the standalone report's interpretation of benchmark result files."""

from itertools import product
import hashlib
import json
import runpy
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
                "stats": {
                    "median": 0.000002 if backend == "json" else 0.000001,
                    "mean": 0.0000021 if backend == "json" else 0.00000105,
                    "stddev": 0.0000003 if backend == "json" else 0.00000015,
                    "q1": 0.0000019 if backend == "json" else 0.00000095,
                    "q3": 0.0000021 if backend == "json" else 0.00000105,
                    "iqr": 0.0000002 if backend == "json" else 0.0000001,
                    "rounds": 20,
                    "iterations": 5,
                },
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
        "Introduction\n<!-- benchmark-summary:start -->\nold summary\n"
        "<!-- benchmark-summary:end -->\n## Run benchmarks\n"
        "<!-- benchmark-results:start -->\nold\n"
        "<!-- benchmark-results:end -->\nAfterword\n"
    )
    command = [
        sys.executable,
        str(REPORT),
        str(result_file),
        "--update",
        str(page),
        "--plots",
        "assets/benchmarking",
    ]
    subprocess.run(command, check=True, capture_output=True)
    first = page.read_text(encoding="utf-8")
    assert "| serialization | simple | json (CPython) | 2 | 0.2 | 2.1 ± 0.3 | 20 × 5 |" in first
    assert "| serialization | simple | 1× | 2× | 2× |" in first
    assert first.index("#### Times and variation") < first.index("#### Speedup")
    assert "assets/benchmarking/python-3.15-times.svg" in first
    assert "assets/benchmarking/python-3.15-speedup.svg" in first
    assert first.index("## Complete-formatting summary") < first.index("## Run benchmarks")
    assert "assets/benchmarking/summary.svg" in first
    assert "Summary values and included versions" not in first
    assert (
        "Timing and speedup coverage for json (CPython), orjson (CPython), msgspec (CPython)"
        in first
    )
    assert first.count('??? note "Timing statistics"') == 1
    assert first.count('??? note "Speedup values"') == 1
    assert "    | serialization | simple" in first
    assert first.startswith("Introduction\n")
    assert first.endswith("Afterword\n")
    subprocess.run(command, check=True, capture_output=True)
    assert page.read_text(encoding="utf-8") == first
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


def test_report_curates_without_changing_statistics(result_file: Path, tmp_path: Path) -> None:
    """Curated JSON preserves summaries and provenance without large sample arrays."""
    result = json.loads(result_file.read_text())
    result["benchmarks"][0]["stats"]["data"] = [0.000002] * 10
    result_file.write_text(json.dumps(result))
    original = result_file.read_bytes()
    target = tmp_path / "curated"
    subprocess.run(
        [sys.executable, str(REPORT), str(result_file), "--curate", str(target)],
        check=True,
        capture_output=True,
    )
    curated = json.loads((target / result_file.name).read_text())
    assert "data" not in curated["benchmarks"][0]["stats"]
    assert curated["benchmarks"][0]["stats"]["median"] == 0.000002
    assert curated["curation"]["source_sha256"] == hashlib.sha256(original).hexdigest()
    assert result_file.read_bytes() == original
    original_report = subprocess.check_output([sys.executable, str(REPORT), str(result_file)])
    curated_report = subprocess.check_output(
        [sys.executable, str(REPORT), str(target / result_file.name)]
    )
    assert original_report == curated_report
    return


def test_report_stdlib_only_pypy(result_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PyPy reports retain stdlib timings and clearly mark unavailable encoders."""
    # Tox can set UTF-8 stdout independently of Windows' preferred locale.
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    cpython_file = result_file.with_name("cpython.json")
    cpython = json.loads(result_file.read_text())
    cpython["environment"]["python"] = "3.15.1"
    cpython_file.write_text(json.dumps(cpython))
    result = json.loads(result_file.read_text())
    result["environment"].update(implementation="PyPy", python="3.15.0", backends=["json"])
    result["benchmarks"] = [
        item for item in result["benchmarks"] if item["extra_info"]["backend"] == "json"
    ]
    for item in result["benchmarks"]:
        for statistic in ("median", "mean", "stddev", "q1", "q3", "iqr"):
            item["stats"][statistic] /= 4
    result_file.write_text(json.dumps(result))
    text = subprocess.check_output(
        [sys.executable, str(REPORT), str(result_file), str(cpython_file)], encoding="utf-8"
    )
    reversed_text = subprocess.check_output(
        [sys.executable, str(REPORT), str(cpython_file), str(result_file)], encoding="utf-8"
    )
    assert text == reversed_text
    assert text.count("### Python 3.15") == 1
    assert "Reference: json (CPython) (1×)." in text
    assert "json (PyPy)" in text
    assert "orjson (PyPy)" not in text
    assert "| --- | --- | ---: | ---: | ---: | ---: |\n    | serialization" in text
    standalone = subprocess.check_output(
        [sys.executable, str(REPORT), str(result_file)], encoding="utf-8"
    )
    assert "Reference: json (PyPy) (1×)." in standalone
    assert "CPython" not in standalone
    assert "**PyPy 3.15.0**" in text
    assert "| serialization | simple | 1× | 2× | 2× | 4× |" in text
    return


def test_report_rejects_duplicate_minor_runtime(result_file: Path) -> None:
    """Two patch versions of one implementation must not overwrite a comparison."""
    other = result_file.with_name("duplicate.json")
    result = json.loads(result_file.read_text())
    result["environment"]["python"] = "3.15.1"
    other.write_text(json.dumps(result))
    completed = subprocess.run(
        [sys.executable, str(REPORT), str(result_file), str(other)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "Duplicate runtime" in completed.stderr
    assert not completed.stdout
    return


def test_formatting_summary_version_ranges() -> None:
    """Average equal-weight version medians and ratios with matched references only."""
    report = runpy.run_path(str(REPORT))
    groups = []
    for version, baseline, other, pypy in (
        ("3.10", 2, 1, 0.5),
        ("3.11", 18, 2, None),
        ("3.12", 20, 5, None),
        ("3.13", None, None, 3),
    ):
        cases = {}
        for workload in report["WORKLOADS"]:
            for backend, value in (
                ("json (CPython)", baseline),
                ("orjson (CPython)", other),
                ("json (PyPy)", pypy),
            ):
                if value is not None:
                    cases["formatting", workload, backend] = {"median": value * 1e-6}
            # Serialization must not affect the complete-formatting summary.
            cases["serialization", workload, "json (CPython)"] = {"median": 100}
        groups.append({"python": version, "cases": cases})
    summary = report["formatting_summary"](groups)
    for workload in report["WORKLOADS"]:
        values = summary[workload]
        assert list(values) == ["json (CPython)", "orjson (CPython)", "json (PyPy)"]
        assert values["orjson (CPython)"]["times"] == {
            "mean": pytest.approx(8 / 3),
            "min": 1,
            "max": 5,
            "versions": ["3.10", "3.11", "3.12"],
        }
        ratios = values["orjson (CPython)"]["speedup"]
        assert ratios["mean"] == pytest.approx(5)
        assert ratios["min"] == pytest.approx(2)
        assert ratios["max"] == pytest.approx(9)
        assert ratios["versions"] == ["3.10", "3.11", "3.12"]
        assert values["json (PyPy)"]["times"]["mean"] == pytest.approx(1.75)
        assert values["json (PyPy)"]["times"]["versions"] == ["3.10", "3.13"]
        assert values["json (PyPy)"]["speedup"] == {
            "mean": 4,
            "min": 4,
            "max": 4,
            "versions": ["3.10"],
        }
    standalone = report["formatting_summary"]([groups[-1]])
    assert "speedup" not in standalone["simple"]["json (PyPy)"]
    text = report["render_summary"]([groups[-1]])
    assert "Timing coverage for json (PyPy): Python 3.13 (n=1)." in text
    assert "Speedup coverage" not in text
    return
