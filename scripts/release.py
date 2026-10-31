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

# Import packaging only in build/metadata commands; publisher preflight uses the stdlib.


def run(*args: str) -> str:
    """Run a checked command."""
    return subprocess.check_output(args, text=True).strip()


def release_info(tag: str, project_version: str, changelog: str) -> tuple[str, str]:
    """Return the normalized version and complete base-version changelog section."""
    from packaging.version import Version  # pylint: disable=import-outside-toplevel

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
    from packaging.version import Version  # pylint: disable=import-outside-toplevel

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
                "run_id": os.environ["GITHUB_RUN_ID"],
                "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
            }
        )
    )
    return None


def validate_distributions(directory: Path, version: str) -> None:
    """Check both metadata records and write a manifest for exactly two files."""
    from packaging.utils import canonicalize_name  # pylint: disable=import-outside-toplevel
    from packaging.version import Version  # pylint: disable=import-outside-toplevel

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
                return None if response.status == 204 else json.load(response)
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


def draft_action(release: dict | None, commit: str) -> str:
    """Choose draft replacement without ever modifying a public release."""
    if release is None:
        return "create"
    if not release["draft"]:
        raise ValueError("Published GitHub release requires owner cleanup")
    return "update" if release["target_commitish"] == commit else "replace"


def live_tag(api: GitHub) -> None:
    """Resolve lightweight or annotated live tags and reject stale runs."""
    ref = api.request(f'/git/ref/tags/{os.environ["GITHUB_REF_NAME"]}')
    if ref is None:
        raise ValueError("Release tag was deleted")
    obj = ref["object"]
    while obj["type"] == "tag":
        obj = api.request(f'/git/tags/{obj["sha"]}')["object"]
    require_current_commit(obj["type"], obj["sha"], os.environ["GITHUB_SHA"])
    return None


def require_current_commit(kind: str, current: str, expected: str) -> None:
    """Reject approvals for moved tags or tags pointing at non-commits."""
    if kind != "commit" or current != expected:
        raise ValueError("Release tag moved; cancel this stale run")
    return None


def eligible(bundle: Path, api: GitHub) -> None:
    """Reject any existing target PyPI version before expensive checks."""
    info = json.loads((bundle / "release.json").read_text())
    live_tag(api)
    draft_action(api.find_release(info["tag"]), info["commit"])
    require_unpublished(pypi_files(info["version"]))
    return None


def stage(bundle: Path, api: GitHub) -> None:
    """Replace all draft assets, recreating the draft when its commit changed."""
    eligible(bundle, api)
    info = json.loads((bundle / "release.json").read_text())
    manifest = verify_bundle(bundle)
    release = api.find_release(info["tag"])
    action = draft_action(release, info["commit"])
    if action == "replace":
        assert release is not None
        api.request(f'/releases/{release["id"]}', method="DELETE")
        release = None
    expected = {
        "tag_name": info["tag"],
        "target_commitish": info["commit"],
        "name": info["tag"][1:],
        "body": (bundle / "notes.md").read_text(),
        "prerelease": info["prerelease"],
        "draft": True,
    }
    if release is None:
        release = api.request("/releases", expected)
    else:
        api.request(f'/releases/{release["id"]}', expected, method="PATCH")
        for asset in api.request(f'/releases/{release["id"]}/assets?per_page=100'):
            api.request(f'/releases/assets/{asset["id"]}', method="DELETE")
    for path in [bundle / "dist" / name for name in manifest] + [
        bundle / "SHA256SUMS.json",
        bundle / "release.json",
    ]:
        subprocess.run(
            [
                "gh",
                "release",
                "upload",
                info["tag"],
                str(path),
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
            ],
            check=True,
        )
    return None


def pypi_files(version: str) -> dict[str, str] | None:
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
            return None
        raise


def require_unpublished(existing: dict[str, str] | None) -> None:
    """Even an empty or yanked version record blocks ordinary publishing."""
    if existing is not None:
        raise ValueError("PyPI version already exists; recover original bytes manually")
    return None


def require_published(manifest: dict[str, str], existing: dict[str, str] | None) -> None:
    """Finalize only an exact, complete publication of the approved bundle."""
    if existing != manifest:
        raise ValueError("PyPI files do not match the complete release manifest")
    return None


def verify_bundle(bundle: Path) -> dict[str, str]:
    """Verify the retained bytes and their binding to the current tag and commit."""
    info = json.loads((bundle / "release.json").read_text())
    if info["tag"] != os.environ["GITHUB_REF_NAME"] or info["commit"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Bundle tag or commit mismatch")
    if info["run_id"] != os.environ["GITHUB_RUN_ID"]:
        raise ValueError("Bundle belongs to a different workflow run")
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
            not re.fullmatch(r"[A-Za-z0-9_.+-]+", name)
            or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or hashlib.sha256((bundle / "dist" / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Invalid filename or checksum mismatch")
    return manifest


def verify_release(bundle: Path, api: GitHub, manifest: dict[str, str]) -> dict:
    """Verify exact GitHub release source, metadata and assets against the bundle."""
    info = json.loads((bundle / "release.json").read_text())
    release = api.find_release(info["tag"])
    if release is None or release["target_commitish"] != info["commit"]:
        raise ValueError("Missing or changed release draft")
    # Compare downloaded assets byte for byte, including attempt identity.
    assets = api.request(f'/releases/{release["id"]}/assets?per_page=100')
    expected = set(manifest) | {"release.json", "SHA256SUMS.json"}
    if {a["name"] for a in assets} != expected:
        raise ValueError("Unexpected release assets")
    for asset in assets:
        content = subprocess.check_output(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/octet-stream",
                f'/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/assets/{asset["id"]}',
            ]
        )
        name = asset["name"]
        path = bundle / "dist" / name if name in manifest else bundle / name
        if content != path.read_bytes():
            raise ValueError("Draft assets differ from approved bundle")
    if release["body"] != (bundle / "notes.md").read_text() or (
        release["prerelease"] != info["prerelease"]
    ):
        raise ValueError("Release metadata differs from approved bundle")
    return release


def preflight(bundle: Path, api: GitHub) -> None:
    """Recheck approved bytes and identities immediately before the PyPI upload."""
    manifest = verify_bundle(bundle)
    verify_release(bundle, api, manifest)
    # Repeat the same eligibility policy after approval, checking PyPI last.
    # Early eligibility allows no draft or an obsolete draft; readiness also
    # requires the exact approved source, metadata and distribution bytes above.
    eligible(bundle, api)
    return None


def finalize(bundle: Path, api: GitHub) -> None:
    """Publish only the original draft after verifying every public PyPI hash."""
    manifest = verify_bundle(bundle)
    live_tag(api)
    info = json.loads((bundle / "release.json").read_text())
    require_published(manifest, pypi_files(info["version"]))
    release = verify_release(bundle, api, manifest)
    if release["draft"]:
        api.request(f'/releases/{release["id"]}', {"draft": False}, method="PATCH")
    return None


def record_finalization(destination: Path) -> None:
    """Retain finalization outcome even when the verification/publish step fails."""
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "finalization.json").write_text(
        json.dumps(
            {
                "run_id": os.environ["GITHUB_RUN_ID"],
                "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "bundle_artifact_id": os.environ["BUNDLE_ID"],
                "finalize": os.environ["FINALIZE"],
            },
            indent=2,
        )
        + "\n"
    )
    return None


def main() -> None:
    """Run a release command without embedding Python programs in workflow YAML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "prepare-release-metadata",
            "check-release-version-eligibility",
            "validate-distributions",
            "stage-github-draft",
            "verify-release-bundle",
            "verify-and-publish-github-release",
            "check-pypi-publication-readiness",
            "record-github-finalization-outcome",
        ],
    )
    parser.add_argument("--bundle", type=Path, default=Path("bundle"))
    args = parser.parse_args()
    if args.command == "prepare-release-metadata":
        prepare(os.environ["GITHUB_REF_NAME"], args.bundle)
    elif args.command == "validate-distributions":
        info = json.loads((args.bundle / "release.json").read_text())
        validate_distributions(args.bundle / "dist", info["version"])
    elif args.command == "stage-github-draft":
        stage(args.bundle, GitHub())
    elif args.command == "check-release-version-eligibility":
        eligible(args.bundle, GitHub())
    elif args.command == "verify-release-bundle":
        verify_bundle(args.bundle)
    elif args.command == "check-pypi-publication-readiness":
        preflight(args.bundle, GitHub())
    elif args.command == "verify-and-publish-github-release":
        finalize(args.bundle, GitHub())
    else:
        record_finalization(Path("evidence"))
    return None


if __name__ == "__main__":
    main()
