"""Record the exact environment alongside pytest-benchmark machine statistics."""

from importlib.metadata import version
import os
import platform
import subprocess
from typing import Any


def pytest_benchmark_update_json(output_json: dict[str, Any]) -> None:
    """Add dependency and source metadata for standalone result consumers."""
    output_json["environment"] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "dependencies": {
            package: version(package)
            for package in ("python-json-logger", "orjson", "msgspec", "pytest", "pytest-benchmark")
        },
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }
    return
