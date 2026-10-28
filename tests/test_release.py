"""Offline release policy and recovery regression tests."""

from email.message import Message
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import Mock
import urllib.error
import zipfile

import pytest

pytest.importorskip("tomllib")

SPEC = importlib.util.spec_from_file_location(
    "release", Path(__file__).parents[1] / "scripts" / "release.py"
)
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def changelog(stamp: str = "2026-10-28", body: str = "### Added\n- A feature.") -> str:
    return f"# Changes\n\n## [4.3.0](compare) - {stamp}\n\n{body}\n\n## [4.2.0](old) - 2026-08-15\nOld\n"


@pytest.mark.parametrize("tag,version", [("v4.3.0", "4.3.0"), ("v4.3.0.rc1", "4.3.0rc1")])
def test_release_info(tag: str, version: str) -> None:
    actual, notes = release.release_info(tag, version, changelog())
    assert actual == version
    assert notes == changelog().split("\n\n", 1)[1].split("## [4.2.0]", 1)[0].rstrip() + "\n"
    return None


@pytest.mark.parametrize(
    "tag", ["4.3.0", "v4.3", "v04.3.0", "v4.3.0rc1", "v4.3.0.dev1", "v4.3.0.rc01", "v4.3.0\n"]
)
def test_invalid_tags(tag: str) -> None:
    with pytest.raises(ValueError):
        release.release_info(tag, "4.3.0", changelog())
    return None


@pytest.mark.parametrize(
    "text",
    [
        changelog(body="### Added\n"),
        changelog() + changelog(),
        changelog().replace("[4.3.0]", "[4.4.0]"),
        changelog(stamp="UNRELEASED"),
        changelog(stamp="2026-02-30"),
    ],
)
def test_invalid_changelog(text: str) -> None:
    with pytest.raises(ValueError):
        release.release_info("v4.3.0", "4.3.0", text)
    return None


def test_rc_unreleased_and_version_mismatch() -> None:
    assert release.release_info("v4.3.0.rc1", "4.3.0.rc1", changelog("UNRELEASED"))[0] == "4.3.0rc1"
    with pytest.raises(ValueError):
        release.release_info("v4.3.0", "4.3.0.dev1", changelog())
    return None


def test_ancestry_rejected_before_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        release.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "git"))
    )
    with pytest.raises(subprocess.CalledProcessError):
        release.prepare("v4.3.0", tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()
    return None


def distributions(tmp_path: Path, version: str = "4.3.0") -> Path:
    directory = tmp_path / "dist"
    directory.mkdir()
    metadata = f"Name: python-json-logger\nVersion: {version}\n".encode()
    with zipfile.ZipFile(directory / "package.whl", "w") as archive:
        archive.writestr("package.dist-info/METADATA", metadata)
    with tarfile.open(directory / "package.tar.gz", "w:gz") as archive:
        member = tarfile.TarInfo("package/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))
    return directory


@pytest.mark.parametrize("version", ["4.3.0", "4.3.0rc1"])
def test_distribution_metadata_and_manifest(tmp_path: Path, version: str) -> None:
    directory = distributions(tmp_path, version)
    release.validate_distributions(directory, version)
    manifest = json.loads((tmp_path / "SHA256SUMS.json").read_text())
    assert manifest == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()
    }
    with pytest.raises(ValueError):
        release.validate_distributions(directory, "4.3.1")
    (directory / "extra.whl").touch()
    with pytest.raises(ValueError):
        release.validate_distributions(directory, "4.3.0")
    return None


def bundle(tmp_path: Path) -> Path:
    release.validate_distributions(distributions(tmp_path), "4.3.0")
    (tmp_path / "notes.md").write_text(changelog())
    (tmp_path / "release.json").write_text(
        json.dumps({"tag": "v4.3.0", "version": "4.3.0", "commit": "abc", "prerelease": False})
    )
    return tmp_path


def draft() -> dict:
    return {
        "id": 42,
        "tag_name": "v4.3.0",
        "target_commitish": "abc",
        "name": "4.3.0",
        "body": changelog(),
        "draft": True,
        "prerelease": False,
    }


def test_create_and_reuse_draft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle(tmp_path)
    api = Mock()
    api.find_release.return_value = None
    api.request.side_effect = [draft(), []]
    upload = Mock()
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(release.subprocess, "run", upload)
    release.stage(tmp_path, api)
    assert api.request.call_args_list[0].args == (
        "/releases",
        {k: v for k, v in draft().items() if k != "id"},
    )
    assert upload.call_count == 3
    api.find_release.return_value = draft()
    api.request.side_effect = [[{"name": "package.whl", "id": 1}]]
    monkeypatch.setattr(
        release.subprocess,
        "check_output",
        Mock(return_value=(tmp_path / "dist/package.whl").read_bytes()),
    )
    upload.reset_mock()
    release.stage(tmp_path, api)
    assert upload.call_count == 2
    return None


@pytest.mark.parametrize(
    "change",
    [{"draft": False}, {"body": "other"}, {"prerelease": True}, {"target_commitish": "other"}],
)
def test_refuse_conflicting_release(tmp_path: Path, change: dict) -> None:
    bundle(tmp_path)
    api = Mock()
    api.find_release.return_value = draft() | change
    with pytest.raises(ValueError):
        release.stage(tmp_path, api)
    return None


def test_conflicting_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle(tmp_path)
    api = Mock()
    api.find_release.return_value = draft()
    api.request.side_effect = [[{"name": "package.whl", "id": 1}]]
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(release.subprocess, "check_output", Mock(return_value=b"different"))
    with pytest.raises(ValueError, match="Conflicting draft asset"):
        release.stage(tmp_path, api)
    return None


# Exercise the actual inline publishing program without network or OIDC credentials.
def publish_program() -> str:
    text = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text()
    source = text.split("      - name: Verify retained bytes and select missing PyPI files", 1)[1]
    source = source.split("          python - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
    return "\n".join(line[10:] for line in source.splitlines())


@pytest.mark.parametrize(
    "state,expected", [("absent", 2), ("partial", 1), ("identical", 0), ("conflict", None)]
)
def test_publish_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, expected: int | None
) -> None:
    bundle(tmp_path)
    # The workflow runs with bundle/ in its working directory.
    root = tmp_path / "workspace"
    root.mkdir()
    (tmp_path / "dist").rename(root / "bundle-dist")
    target = root / "bundle"
    target.mkdir()
    (root / "bundle-dist").rename(target / "dist")
    for name in ("release.json", "SHA256SUMS.json", "notes.md"):
        (tmp_path / name).rename(target / name)
    monkeypatch.chdir(root)
    monkeypatch.setenv("RELEASE_TAG", "v4.3.0")
    monkeypatch.setenv("RELEASE_COMMIT", "abc")
    monkeypatch.setenv("GITHUB_OUTPUT", str(root / "output"))
    manifest = json.loads((target / "SHA256SUMS.json").read_text())
    files = list(manifest.items())
    if state == "absent":
        response = Mock(side_effect=urllib.error.HTTPError("url", 404, "missing", Message(), None))
    else:
        if state == "partial":
            files = files[:1]
        if state == "conflict":
            files[0] = (files[0][0], "wrong")
        payload = {"urls": [{"filename": n, "digests": {"sha256": d}} for n, d in files]}
        response = Mock(return_value=io.BytesIO(json.dumps(payload).encode()))
    monkeypatch.setattr("urllib.request.urlopen", response)
    if expected is None:
        with pytest.raises(SystemExit, match="conflict"):
            exec(publish_program(), {})
    else:
        exec(publish_program(), {})
        uploaded = list((root / "upload").iterdir())
        assert len(uploaded) == expected
        for path in uploaded:
            assert path.read_bytes() == (target / "dist" / path.name).read_bytes()
    return None


def test_stage_checksum_mismatch_before_network(tmp_path: Path) -> None:
    bundle(tmp_path)
    (tmp_path / "dist/package.whl").write_bytes(b"tampered")
    api = Mock()
    with pytest.raises(ValueError, match="checksum mismatch"):
        release.stage(tmp_path, api)
    api.request.assert_not_called()
    return None


def test_stage_unexpected_asset(tmp_path: Path) -> None:
    bundle(tmp_path)
    api = Mock()
    api.find_release.return_value = draft()
    api.request.side_effect = [[{"name": "unexpected", "id": 1}]]
    with pytest.raises(ValueError, match="Unexpected draft assets"):
        release.stage(tmp_path, api)
    return None


def test_api_errors_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GH_TOKEN", "fake")
    client = release.GitHub()
    for code in (403, 500):
        monkeypatch.setattr(
            "urllib.request.urlopen",
            Mock(side_effect=urllib.error.HTTPError("url", code, "error", Message(), None)),
        )
        with pytest.raises(urllib.error.HTTPError):
            client.request("/releases/tags/v4.3.0")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        Mock(side_effect=urllib.error.HTTPError("url", 404, "missing", Message(), None)),
    )
    assert client.request("/releases/tags/v4.3.0") is None
    with pytest.raises(urllib.error.HTTPError):
        client.request("/releases", {})
    return None


def test_workflow_boundaries() -> None:
    yaml = pytest.importorskip("yaml")
    path = Path(__file__).parents[1] / ".github/workflows"
    workflow = yaml.load((path / "release.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["on"] == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    jobs = workflow["jobs"]
    assert jobs["ci"]["needs"] == "validate"
    assert jobs["ci"]["uses"] == "./.github/workflows/test-suite.yml"
    assert set(jobs["build"]["needs"]) == {"validate", "ci"}
    assert jobs["draft"]["needs"] == "build"
    assert jobs["publish"]["needs"] == "draft"
    assert jobs["publish"]["environment"]["name"] == "pypi"
    for name, job in jobs.items():
        permissions = job.get("permissions", {})
        assert (permissions.get("contents") == "write") == (name == "draft")
        assert (permissions.get("id-token") == "write") == (name == "publish")
        for step in job.get("steps", []):
            if "uses" in step:
                assert len(step["uses"].split("@")[1]) == 40
    publish = jobs["publish"]
    assert not any("checkout" in step.get("uses", "") for step in publish["steps"])
    assert not any("scripts/" in step.get("run", "") for step in publish["steps"])
    assert "skip-existing" not in str(publish)
    ci = yaml.load((path / "test-suite.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(ci["on"]) == {"workflow_call", "push", "pull_request"}
    assert set(ci["jobs"]["test"]["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "windows-latest",
        "macos-latest",
    }
    return None


def test_draft_lookup_pagination_and_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    client = release.GitHub()
    request = Mock(side_effect=[[{"tag_name": "v0.0.0"}] * 100, [draft()]])
    monkeypatch.setattr(client, "request", request)
    assert client.find_release("v4.3.0") == draft()
    assert request.call_args_list[1].args == ("/releases?per_page=100&page=2",)
    request.side_effect = [[draft(), draft()]]
    with pytest.raises(ValueError, match="Multiple releases"):
        client.find_release("v4.3.0")
    request.side_effect = [[]]
    assert client.find_release("v4.3.0") is None
    return None


@pytest.mark.parametrize("state", ["checksum", "commit", "unavailable"])
def test_publisher_fails_before_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    bundle(tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    target = work / "bundle"
    target.mkdir()
    for name in ("dist", "release.json", "SHA256SUMS.json", "notes.md"):
        (tmp_path / name).rename(target / name)
    monkeypatch.chdir(work)
    monkeypatch.setenv("RELEASE_TAG", "v4.3.0")
    monkeypatch.setenv("RELEASE_COMMIT", "wrong" if state == "commit" else "abc")
    monkeypatch.setenv("GITHUB_OUTPUT", str(work / "output"))
    if state == "checksum":
        (target / "dist/package.whl").write_bytes(b"corrupt")
    network = Mock(side_effect=urllib.error.HTTPError("url", 503, "unavailable", Message(), None))
    monkeypatch.setattr("urllib.request.urlopen", network)
    with pytest.raises(urllib.error.HTTPError if state == "unavailable" else AssertionError):
        exec(publish_program(), {})
    if state != "unavailable":
        network.assert_not_called()
    assert not (work / "upload").exists()
    return None


@pytest.mark.parametrize("state", ["new", "previous-run", "lost-bundle", "published", "pypi"])
def test_rebuild_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    text = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text()
    source = text.split("      - name: Refuse to rebuild an existing release", 1)[1]
    source = source.split("          python - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
    program = "\n".join(line[10:] for line in source.splitlines())
    target = tmp_path / "bundle"
    target.mkdir()
    (target / "release.json").write_text(json.dumps({"tag": "v4.3.0", "version": "4.3.0"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_RUN_ID", "100")
    monkeypatch.setitem(sys.modules, "release", release)
    api = Mock()
    runs = [{"id": 100, "head_branch": "v4.3.0"}]
    if state == "previous-run":
        runs.append({"id": 99, "head_branch": "v4.3.0"})
    jobs = (
        [{"name": "build", "conclusion": "success", "started_at": "date"}]
        if state == "lost-bundle"
        else []
    )
    api.request.side_effect = [
        {"workflow_runs": runs},
        {"jobs": jobs},
        draft() if state == "published" else None,
    ]
    monkeypatch.setattr(release, "GitHub", Mock(return_value=api))
    network = Mock(side_effect=urllib.error.HTTPError("url", 404, "missing", Message(), None))
    if state == "pypi":
        network.side_effect = None
    monkeypatch.setattr("urllib.request.urlopen", network)
    if state == "new":
        exec(program, {})
    else:
        with pytest.raises(SystemExit):
            exec(program, {})
    return None
