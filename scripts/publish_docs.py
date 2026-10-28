"""Build Mike history locally; the workflow pushes only after successful builds."""

import json
import subprocess
import tomllib
from pathlib import Path

from packaging.version import Version


def documentation_version(value: str) -> tuple[str, bool]:
    """Return the public documentation label and whether it is stable."""
    version = Version(value)
    if version.local is not None:
        raise ValueError("Local versions cannot be published")
    development = version.is_devrelease or version.is_prerelease
    return ("dev" if development else str(version)), not development


def main() -> None:
    """Update the local gh-pages branch without pushing partial changes."""
    value = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    label, stable = documentation_version(value)
    command = ["mike", "deploy", label]
    if stable:
        command += ["latest", "--update-aliases"]
    subprocess.run(command, check=True)
    if stable:
        # Mike rejects deletion of a missing version, including on release reruns.
        versions = json.loads(subprocess.check_output(["mike", "list", "--json"]))
        if any(item["version"] == "dev" for item in versions):
            subprocess.run(["mike", "delete", "dev"], check=True)


if __name__ == "__main__":
    main()
