"""Unit tests for release policy; no external build, Git, or API integration tests."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("tomllib")
ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def changelog(stamp: str = "2026-10-28", body: str = "### Added\n- A feature.") -> str:
    return f"# Changes\n\n## [4.3.0](compare) - {stamp}\n\n{body}\n\n## [4.2.0](old) - 2026-08-15\nOld\n"


@pytest.mark.parametrize(
    "tag,version",
    [
        ("v4.3.0", "4.3.0"),
        ("v4.3.0.rc1", "4.3.0rc1"),
        ("v4.3.0.dev1", "4.3.0.dev1"),
        ("v4.3.0.post1", "4.3.0.post1"),
    ],
)
def test_release_info(tag: str, version: str) -> None:
    actual, notes = release.release_info(tag, version, changelog())
    assert actual == version
    assert notes == changelog().split("\n\n", 1)[1].split("## [4.2.0]", 1)[0].rstrip() + "\n"
    return None


@pytest.mark.parametrize(
    "tag",
    [
        "4.3.0",
        "v4.3",
        "v04.3.0",
        "v4.3.0rc1",
        "v4.3.0.rc01",
        "v4.3.0\n",
        "vladamir/test-the-new-thing",
        "v4.3.0a1",
        "v4.3.0.rc1.extra",
    ],
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


@pytest.mark.parametrize(
    "tag,version",
    [("v4.3.0", "4.3.0"), ("v4.3.0.rc1", "4.3.0rc1"), ("v4.3.0.post1", "4.3.0.post1")],
)
def test_non_development_requires_date(tag: str, version: str) -> None:
    with pytest.raises(ValueError, match="requires a changelog date"):
        release.release_info(tag, version, changelog("UNRELEASED"))
    return None


def test_development_unreleased_and_version_mismatch() -> None:
    assert (
        release.release_info("v4.3.0.dev1", "4.3.0.dev1", changelog("UNRELEASED"))[0]
        == "4.3.0.dev1"
    )
    with pytest.raises(ValueError):
        release.release_info("v4.3.0", "4.3.0.dev1", changelog())
    return None


def test_postrelease_preserves_original_date() -> None:
    text = changelog("2025-01-02")
    _, notes = release.release_info("v4.3.0.post1", "4.3.0.post1", text)
    assert notes.startswith("## [4.3.0](compare) - 2025-01-02\n")
    return None


@pytest.mark.parametrize("existing", [{}, {"wheel": "aaa"}, {"wheel": "aaa", "sdist": "bbb"}])
def test_any_pypi_record_blocks_new_release(existing: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="already exists"):
        release.require_unpublished(existing)
    return None


def test_absent_version_is_eligible() -> None:
    release.require_unpublished(None)
    return None


@pytest.mark.parametrize(
    "existing", [None, {}, {"wheel": "aaa"}, {"wheel": "wrong", "sdist": "bbb"}]
)
def test_finalize_requires_complete_matching_publication(existing: dict[str, str] | None) -> None:
    with pytest.raises(ValueError, match="complete release manifest"):
        release.require_published({"wheel": "aaa", "sdist": "bbb"}, existing)
    return None


def test_complete_publication_can_finalize() -> None:
    release.require_published({"wheel": "aaa", "sdist": "bbb"}, {"wheel": "aaa", "sdist": "bbb"})
    return None


@pytest.mark.parametrize("commit,expected", [("abc", "update"), ("def", "replace")])
def test_draft_commit_policy(commit: str, expected: str) -> None:
    assert release.draft_action({"draft": True, "target_commitish": commit}, "abc") == expected
    return None


def test_public_release_requires_owner_cleanup() -> None:
    assert release.draft_action(None, "abc") == "create"
    with pytest.raises(ValueError, match="owner cleanup"):
        release.draft_action({"draft": False, "target_commitish": "abc"}, "abc")
    return None


@pytest.mark.parametrize("kind,current", [("commit", "old"), ("tree", "approved")])
def test_stale_run_cannot_publish(kind: str, current: str) -> None:
    with pytest.raises(ValueError, match="stale run"):
        release.require_current_commit(kind, current, "approved")
    return None


def test_live_source_matches_approval() -> None:
    release.require_current_commit("commit", "approved", "approved")
    return None


def test_bundle_identity_and_checksums(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "dist"
    directory.mkdir()
    # Treat distributions as opaque bytes: this checks our retained-file policy.
    files = {"package.whl": b"wheel bytes", "package.tar.gz": b"sdist bytes"}
    for name, content in files.items():
        (directory / name).write_bytes(content)
    (tmp_path / "SHA256SUMS.json").write_text(
        json.dumps({name: hashlib.sha256(content).hexdigest() for name, content in files.items()})
    )
    (tmp_path / "release.json").write_text(
        json.dumps({"tag": "v4.3.0", "commit": "abc", "run_id": "123"})
    )
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_REF_NAME", "v4.3.0")
    monkeypatch.setenv("GITHUB_SHA", "wrong")
    with pytest.raises(ValueError, match="commit mismatch"):
        release.verify_bundle(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", "abc")
    assert set(release.verify_bundle(tmp_path)) == {"package.whl", "package.tar.gz"}
    monkeypatch.setenv("GITHUB_RUN_ID", "another-run")
    with pytest.raises(ValueError, match="different workflow run"):
        release.verify_bundle(tmp_path)
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    (directory / "package.whl").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        release.verify_bundle(tmp_path)
    return None


def test_workflow_permissions_and_order() -> None:
    yaml = pytest.importorskip("yaml")
    text = (ROOT / ".github/workflows/release.yml").read_text()
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert "python - <<" not in text
    assert workflow["on"] == {"push": {"tags": ["v[0-9]*.[0-9]*.[0-9]*"]}}
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    for job, dependency in (
        ("ci", "validate"),
        ("draft", "build"),
    ):
        assert jobs[job]["needs"] == dependency
    for name, job in jobs.items():
        permissions = job.get("permissions", {})
        assert (permissions.get("contents") == "write") == (name in ("draft", "finalize"))
        assert (permissions.get("id-token") == "write") == (name == "publish")
        for step in job.get("steps", []):
            if "uses" in step:
                assert len(step["uses"].split("@")[1]) == 40
    assert jobs["publish"]["environment"]["name"] == "pypi"
    assert jobs["publish"]["needs"] == ["build", "draft"]
    assert jobs["finalize"]["needs"] == ["build", "publish"]
    assert "needs.publish.outputs.uploaded == 'success'" in jobs["finalize"]["if"]
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    assert jobs["ci"]["needs"] == "validate"
    assert "eligible" in jobs["validate"]["steps"][-1]["run"]
    build = jobs["build"]["steps"]
    assert not any("recover" in step.get("run", "") for step in build)
    assert any("python -m build" in step.get("run", "") for step in build)
    assert build[-1]["with"]["name"] == "release-bundle-${{ github.run_attempt }}"
    assert "select" not in jobs
    for name in ("draft", "publish", "finalize"):
        download = next(s for s in jobs[name]["steps"] if "download-artifact" in s.get("uses", ""))
        assert download["with"]["artifact-ids"] == "${{ needs.build.outputs.bundle-id }}"
    steps = jobs["publish"]["steps"]
    checkout = next(s for s in steps if "checkout" in s.get("uses", ""))
    assert checkout["with"] == {
        "ref": "${{ github.sha }}",
        "persist-credentials": "false",
        "sparse-checkout": "scripts/release.py",
        "sparse-checkout-cone-mode": "false",
    }
    assert not any("pip install" in s.get("run", "") for s in steps)
    assert not any("gh release edit" in step.get("run", "") for step in steps)
    preflight = next(s for s in steps if s.get("id") == "preflight")
    assert preflight["run"] == "python -I scripts/release.py preflight"
    upload = next(s for s in steps if s.get("id") == "upload")
    assert "pypa/gh-action-pypi-publish@" in upload["uses"]
    assert upload["with"]["packages-dir"] == "bundle/dist/"
    evidence = steps[-2]
    assert evidence["if"] == "always()"
    assert "*.publish.attestation" in evidence["run"]
    assert "attestation_status" in evidence["run"]
    assert steps[-1]["if"] == "always()"
    assert steps[-1]["with"]["retention-days"] == "90"
    return None


@pytest.mark.parametrize("date", ["2025-01-02", "2026-01-02"])
def test_postrelease_date_policy(date: str) -> None:
    original = "## [4.2.0](compare) - 2025-01-02\n\n- Original changes.\n"
    post = f"## [4.2.0](compare) - {date}\n\n- Extra post-release changes.\n"
    if date == "2025-01-02":
        release.validate_post_date(post, original)
    else:
        with pytest.raises(ValueError, match="retain the base release date"):
            release.validate_post_date(post, original)
    return None


@pytest.mark.parametrize("outcome", ["success", "failure", "skipped"])
def test_finalization_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    for key, value in {
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "2",
        "BUNDLE_ID": "original-build-id",
        "FINALIZE": outcome,
    }.items():
        monkeypatch.setenv(key, value)
    release.record_finalization(tmp_path / "evidence")
    assert json.loads((tmp_path / "evidence/finalization.json").read_text()) == {
        "run_id": "123",
        "run_attempt": "2",
        "bundle_artifact_id": "original-build-id",
        "finalize": outcome,
    }
    return None
