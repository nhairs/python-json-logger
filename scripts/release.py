"""Validate release inputs and stage immutable release assets. Requires Python 3.12+."""

import argparse
from datetime import date
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
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
        r"v((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))(?:\.(dev|rc|post)(0|[1-9][0-9]*))?",
        tag,
    )
    if not match:
        raise ValueError("Expected vN.N.N with optional .devN, .rcN, or .postN")
    base, phase, number = match.groups()
    version = Version(base + (f".{phase}{number}" if phase is not None else ""))
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
    elif not version.is_devrelease:
        raise ValueError("Non-development release requires a changelog date")
    if not any(line.strip() and not line.startswith("#") for line in body.splitlines()):
        raise ValueError("Empty changelog section")
    return str(version), section


def validate_post_date(notes: str, original_notes: str) -> None:
    """Reject changing the base release date when preparing a post release."""
    original_date = original_notes.split("\n", 1)[0].rsplit(" - ", 1)[1]
    release_date = notes.split("\n", 1)[0].rsplit(" - ", 1)[1]
    if release_date != original_date:
        raise ValueError("Post release must retain the base release date")
    return None


def prepare(tag: str, destination: Path) -> None:
    """Validate tag ancestry and write release metadata."""
    subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], check=True)
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    version, notes = release_info(tag, project["version"], Path("docs/changelog.md").read_text())
    parsed = Version(version)
    if parsed.is_postrelease:
        base = parsed.base_version
        original = run("git", "show", f"refs/tags/v{base}:docs/changelog.md")
        _, original_notes = release_info(f"v{base}", base, original)
        validate_post_date(notes, original_notes)
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
    """Stage exact assets; reuse matching published releases without modifying them."""
    info = json.loads((bundle / "release.json").read_text())
    notes = (bundle / "notes.md").read_text()
    manifest = verify_bundle(bundle)
    assets = {name: (bundle / "dist" / name).read_bytes() for name in manifest}
    assets["SHA256SUMS.json"] = (bundle / "SHA256SUMS.json").read_bytes()
    assets["release.json"] = (bundle / "release.json").read_bytes()
    release = api.find_release(info["tag"])
    expected = {
        "tag_name": info["tag"],
        "target_commitish": info["commit"],
        "name": info["tag"][1:],
        "body": notes,
        "prerelease": info["prerelease"],
    }
    if release is None:
        release = api.request("/releases", expected | {"draft": True})
    elif any(release[key] != value for key, value in expected.items()):
        raise ValueError("Existing release does not match this bundle")
    existing = api.request(f'/releases/{release["id"]}/assets?per_page=100')
    if any(asset["name"] not in assets for asset in existing):
        raise ValueError("Unexpected release assets")
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
                raise ValueError(f"Conflicting release asset: {name}")
        else:
            missing.append(name)
    if not release["draft"] and missing:
        raise ValueError("Published GitHub release has missing assets")
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


def pypi_files(version: str) -> dict[str, str]:
    """Read published hashes; only HTTP 404 means that a version is absent."""
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/python-json-logger/{version}/json", timeout=30
        ) as response:
            return {
                item["filename"]: item["digests"]["sha256"] for item in json.load(response)["urls"]
            }
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {}
        raise


def missing_files(manifest: dict[str, str], existing: dict[str, str]) -> set[str]:
    """Select missing filenames only after every existing filename and hash matches."""
    if any(name not in manifest or manifest[name] != digest for name, digest in existing.items()):
        raise ValueError("PyPI files conflict with retained manifest")
    return set(manifest) - set(existing)


def verify_bundle(bundle: Path) -> dict[str, str]:
    """Verify the retained bytes and their binding to the current tag and commit."""
    info = json.loads((bundle / "release.json").read_text())
    if info["tag"] != os.environ["GITHUB_REF_NAME"] or info["commit"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Bundle tag or commit mismatch")
    manifest = json.loads((bundle / "SHA256SUMS.json").read_text())
    if len(manifest) != 2 or set(manifest) != {p.name for p in (bundle / "dist").iterdir()}:
        raise ValueError("Unexpected distribution manifest")
    if (
        sum(n.endswith(".whl") for n in manifest) != 1
        or sum(n.endswith(".tar.gz") for n in manifest) != 1
    ):
        raise ValueError("Expected a wheel and an sdist")
    for name, digest in manifest.items():
        if (
            Path(name).name != name
            or hashlib.sha256((bundle / "dist" / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Invalid filename or checksum mismatch")
    return manifest


def output(name: str, value: bool) -> None:
    """Set a boolean GitHub Actions step output."""
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"{name}={str(value).lower()}\n")
    return None


def recover(bundle: Path, api: GitHub) -> None:
    """Recover this run's artifact, falling back to verified official release assets."""
    run_id = os.environ["GITHUB_RUN_ID"]
    artifacts = []
    page = 1
    while True:
        entries = api.request(f"/actions/runs/{run_id}/artifacts?per_page=100&page={page}")[
            "artifacts"
        ]
        artifacts.extend(a for a in entries if a["name"] == "release-bundle")
        if len(entries) < 100:
            break
        page += 1
    if len(artifacts) > 1:
        raise ValueError("Ambiguous bundle; recover manually")
    if not artifacts or artifacts[0]["expired"]:
        recovered = recover_published(bundle, api)
        if not recovered and artifacts:
            raise ValueError("Expired bundle without an official release; recover manually")
        output("recovered", recovered)
        output("retained", False)
        return None
    if artifacts:
        subprocess.run(
            ["gh", "run", "download", run_id, "-n", "release-bundle", "-D", str(bundle)], check=True
        )
    output("recovered", bool(artifacts))
    output("retained", bool(artifacts))
    return None


def recover_published(bundle: Path, api: GitHub) -> bool:
    """Restore original bytes from a matching official release, never rebuild them."""
    tag = os.environ["GITHUB_REF_NAME"]
    published = api.request(f"/releases/tags/{tag}")
    if published is None:
        return False
    if published["draft"]:
        raise ValueError("Expected a published release for public artifact recovery")
    prepare(tag, bundle)
    info = json.loads((bundle / "release.json").read_text())
    notes = (bundle / "notes.md").read_text()
    expected = {
        "tag_name": tag,
        "target_commitish": info["commit"],
        "name": tag[1:],
        "body": notes,
        "prerelease": info["prerelease"],
    }
    if any(published[key] != value for key, value in expected.items()):
        raise ValueError("Published release differs from the tagged source")
    # Retain the exact metadata asset rather than reserializing it on recovery.
    (bundle / "release.json").unlink()
    subprocess.run(
        [
            "gh",
            "release",
            "download",
            tag,
            "--pattern",
            "release.json",
            "--pattern",
            "SHA256SUMS.json",
            "--dir",
            str(bundle),
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
        ],
        check=True,
    )
    if json.loads((bundle / "release.json").read_text()) != info:
        raise ValueError("Published release metadata differs from the tagged source")
    manifest = json.loads((bundle / "SHA256SUMS.json").read_text())
    if len(manifest) != 2 or any(Path(name).name != name for name in manifest):
        raise ValueError("Invalid published distribution manifest")
    names = {a["name"] for a in api.request(f'/releases/{published["id"]}/assets?per_page=100')}
    if names != set(manifest) | {"release.json", "SHA256SUMS.json"}:
        raise ValueError("Unexpected published release assets")
    destination = bundle / "dist"
    destination.mkdir()
    for name in manifest:
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                tag,
                "--pattern",
                name,
                "--dir",
                str(destination),
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
            ],
            check=True,
        )
    verify_bundle(bundle)
    return True


def guard_rebuild(bundle: Path, api: GitHub) -> None:
    """Refuse rebuilding a previous release when its retained bytes are unavailable."""
    info = json.loads((bundle / "release.json").read_text())
    run_id = os.environ["GITHUB_RUN_ID"]
    page = 1
    while True:
        runs = api.request(
            f"/actions/workflows/release.yml/runs?event=push&per_page=100&page={page}"
        )["workflow_runs"]
        if any(str(r["id"]) != run_id and r["head_branch"] == info["tag"] for r in runs):
            raise ValueError("Previous run for this tag: recover the original run")
        if len(runs) < 100:
            break
        page += 1
    page = 1
    while True:
        jobs = api.request(f"/actions/runs/{run_id}/jobs?filter=all&per_page=100&page={page}")[
            "jobs"
        ]
        if any(
            (j["name"] == "build" and j["conclusion"] == "success")
            or (
                j["name"] == "draft"
                and j["started_at"] is not None
                and j["conclusion"] != "skipped"
            )
            for j in jobs
        ):
            raise ValueError("Previous bundle unavailable after build/staging: recover manually")
        if len(jobs) < 100:
            break
        page += 1
    if api.request("/releases/tags/" + info["tag"]) is not None or pypi_files(info["version"]):
        raise ValueError("Existing release: restore retained artifacts manually")
    return None


def select_upload(bundle: Path) -> None:
    """Verify and copy missing files in a read-only job before the approval gate."""
    manifest = verify_bundle(bundle)
    info = json.loads((bundle / "release.json").read_text())
    missing = missing_files(manifest, pypi_files(info["version"]))
    destination = Path("upload")
    destination.mkdir()
    for name in missing:
        shutil.copyfile(bundle / "dist" / name, destination / name)
    output("missing", bool(missing))
    return None


def main() -> None:
    """Run a release command without embedding Python programs in workflow YAML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "prepare",
            "validate",
            "stage",
            "recover",
            "guard",
            "verify",
            "select",
        ],
    )
    parser.add_argument("--bundle", type=Path, default=Path("bundle"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(os.environ["GITHUB_REF_NAME"], args.bundle)
    elif args.command == "validate":
        info = json.loads((args.bundle / "release.json").read_text())
        validate_distributions(args.bundle / "dist", info["version"])
    elif args.command == "stage":
        stage(args.bundle, GitHub())
    elif args.command == "recover":
        recover(args.bundle, GitHub())
    elif args.command == "guard":
        guard_rebuild(args.bundle, GitHub())
    elif args.command == "verify":
        verify_bundle(args.bundle)
    else:
        select_upload(args.bundle)
    return None


if __name__ == "__main__":
    main()
