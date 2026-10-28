"""Validate release inputs and stage immutable release assets. Requires Python 3.12+."""

import argparse
from datetime import date
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib
from typing import Any
import urllib.error
import urllib.request
import zipfile

from packaging.utils import canonicalize_name
from packaging.version import Version


def run(*args: str) -> str:
    """Run a checked command."""
    return subprocess.check_output(args, text=True).strip()


def release_info(tag: str, project_version: str, changelog: str) -> tuple[str, str]:
    """Return the normalized version and complete base-version changelog section."""
    match = re.fullmatch(
        r"v((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))(?:\.rc(0|[1-9][0-9]*))?", tag
    )
    if not match:
        raise ValueError("Expected vN.N.N or vN.N.N.rcN")
    base, rc = match.groups()
    version = Version(base + (f"rc{rc}" if rc is not None else ""))
    if Version(project_version) != version:
        raise ValueError("Tag and pyproject versions differ")
    sections = re.split(r"(?m)(?=^## )", changelog)
    entries = [s for s in sections if re.match(rf"^## \[{re.escape(base)}\](?:\(|\s)", s)]
    if len(entries) != 1:
        raise ValueError("Expected exactly one changelog section")
    section = entries[0].rstrip() + "\n"
    heading, body = section.split("\n", 1)
    stamp = heading.rsplit(" - ", 1)[-1]
    if stamp != "UNRELEASED":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", stamp):
            raise ValueError("Expected YYYY-MM-DD changelog date")
        date.fromisoformat(stamp)
    elif rc is None:
        raise ValueError("Stable release requires a changelog date")
    if not any(line.strip() and not line.startswith("#") for line in body.splitlines()):
        raise ValueError("Empty changelog section")
    return str(version), section


def prepare(tag: str, destination: Path) -> None:
    """Validate tag ancestry and write release metadata."""
    subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], check=True)
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    version, notes = release_info(tag, project["version"], Path("docs/changelog.md").read_text())
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "notes.md").write_text(notes)
    (destination / "release.json").write_text(
        json.dumps(
            {
                "tag": tag,
                "version": version,
                "commit": run("git", "rev-parse", "HEAD"),
                "prerelease": Version(version).is_prerelease,
            }
        )
    )
    return None


def validate_distributions(directory: Path, version: str) -> None:
    """Check both metadata records and write a manifest for exactly two files."""
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1 or len(list(directory.iterdir())) != 2:
        raise ValueError("Expected exactly one wheel and one sdist")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("Invalid wheel metadata")
        metadata = [archive.read(names[0])]
    with tarfile.open(sdists[0]) as archive:
        names = [n for n in archive.getnames() if n.count("/") == 1 and n.endswith("/PKG-INFO")]
        if len(names) != 1:
            raise ValueError("Invalid sdist metadata")
        stream = archive.extractfile(names[0])
        if stream is None:
            raise ValueError("Invalid sdist metadata entry")
        metadata.append(stream.read())
    for raw in metadata:
        message = BytesParser().parsebytes(raw)
        if canonicalize_name(message["Name"]) != "python-json-logger" or Version(
            message["Version"]
        ) != Version(version):
            raise ValueError("Distribution metadata differs from release")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels + sdists}
    (directory.parent / "SHA256SUMS.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    return None


class GitHub:
    """Small API client; only a missing resource is treated as absent."""

    def __init__(self) -> None:
        """Use the repository and token supplied by the staging job."""
        self.root = f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}'
        return None

    def request(self, path: str, data: dict | None = None, method: str | None = None) -> Any:
        """Read or create an API resource, returning None only for a missing read."""
        request = urllib.request.Request(
            self.root + path,
            method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Authorization": f'Bearer {os.environ["GH_TOKEN"]}',
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and method is None and data is None:
                return None
            raise
        return None

    def find_release(self, tag: str) -> dict | None:
        """Find drafts as well as published releases, across all listing pages."""
        matches = []
        page = 1
        while True:
            entries = self.request(f"/releases?per_page=100&page={page}")
            if not isinstance(entries, list):
                raise ValueError("Cannot inspect release history")
            matches.extend(entry for entry in entries if entry["tag_name"] == tag)
            if len(entries) < 100:
                break
            page += 1
        if len(matches) > 1:
            raise ValueError("Multiple releases refer to this tag")
        return matches[0] if matches else None


def stage(bundle: Path, api: GitHub) -> None:
    """Create or reuse a matching draft; never overwrite existing assets."""
    info = json.loads((bundle / "release.json").read_text())
    notes = (bundle / "notes.md").read_text()
    manifest = json.loads((bundle / "SHA256SUMS.json").read_text())
    if len(manifest) != 2 or set(manifest) != {p.name for p in (bundle / "dist").iterdir()}:
        raise ValueError("Unexpected distribution manifest")
    if any(Path(name).name != name for name in manifest):
        raise ValueError("Invalid distribution filename")
    assets = {name: (bundle / "dist" / name).read_bytes() for name in manifest}
    assets["SHA256SUMS.json"] = (bundle / "SHA256SUMS.json").read_bytes()
    for name, digest in manifest.items():
        if hashlib.sha256(assets[name]).hexdigest() != digest:
            raise ValueError("Local checksum mismatch")
    release = api.find_release(info["tag"])
    expected = {
        "tag_name": info["tag"],
        "target_commitish": info["commit"],
        "name": info["tag"][1:],
        "body": notes,
        "draft": True,
        "prerelease": info["prerelease"],
    }
    if release is None:
        release = api.request("/releases", expected)
    elif any(release[key] != value for key, value in expected.items()):
        raise ValueError("Existing release is published or does not match this draft")
    existing = api.request(f'/releases/{release["id"]}/assets?per_page=100')
    if any(asset["name"] not in assets for asset in existing):
        raise ValueError("Unexpected draft assets")
    missing = []
    for name, content in assets.items():
        found = [a for a in existing if a["name"] == name]
        if found:
            # Download through the authenticated API, including private draft assets.
            result = subprocess.check_output(
                [
                    "gh",
                    "api",
                    "-H",
                    "Accept: application/octet-stream",
                    f'/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/assets/{found[0]["id"]}',
                ]
            )
            if result != content:
                raise ValueError(f"Conflicting draft asset: {name}")
        else:
            missing.append(name)
    for name in missing:
        subprocess.run(
            [
                "gh",
                "release",
                "upload",
                info["tag"],
                str(bundle / ("dist/" + name if name in manifest else name)),
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
            ],
            check=True,
        )
    return None


def main() -> None:
    """Run a release preparation, validation, or staging command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "validate", "stage"])
    parser.add_argument("--bundle", type=Path, default=Path("bundle"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(os.environ["GITHUB_REF_NAME"], args.bundle)
    elif args.command == "validate":
        info = json.loads((args.bundle / "release.json").read_text())
        validate_distributions(args.bundle / "dist", info["version"])
    else:
        stage(args.bundle, GitHub())
    return None


if __name__ == "__main__":
    main()
