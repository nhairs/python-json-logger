"""Record the exact environment alongside pytest-benchmark machine statistics."""

from importlib.metadata import PackageNotFoundError, version
import os
import platform
import subprocess
from typing import Any


def pytest_benchmark_update_json(output_json: dict[str, Any]) -> None:
    """Add dependency and source metadata for standalone result consumers."""
    dependencies = {}
    for package in ("python-json-logger", "orjson", "msgspec", "pytest", "pytest-benchmark"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            if package not in ("orjson", "msgspec"):
                raise
    output_json["environment"] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "dependencies": dependencies,
        "backends": ["json"] + [name for name in ("orjson", "msgspec") if name in dependencies],
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }
    return
