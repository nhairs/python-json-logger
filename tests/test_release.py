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


@pytest.mark.parametrize(
    "existing,expected",
    [
        ({}, {"wheel", "sdist"}),
        ({"wheel": "aaa"}, {"sdist"}),
        ({"wheel": "aaa", "sdist": "bbb"}, set()),
    ],
)
def test_missing_files(existing: dict[str, str], expected: set[str]) -> None:
    assert release.missing_files({"wheel": "aaa", "sdist": "bbb"}, existing) == expected
    return None


@pytest.mark.parametrize("existing", [{"wheel": "wrong"}, {"unexpected": "aaa"}])
def test_conflicting_pypi_files(existing: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="conflict"):
        release.missing_files({"wheel": "aaa", "sdist": "bbb"}, existing)
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
    (tmp_path / "release.json").write_text(json.dumps({"tag": "v4.3.0", "commit": "abc"}))
    monkeypatch.setenv("GITHUB_REF_NAME", "v4.3.0")
    monkeypatch.setenv("GITHUB_SHA", "wrong")
    with pytest.raises(ValueError, match="commit mismatch"):
        release.verify_bundle(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", "abc")
    assert set(release.verify_bundle(tmp_path)) == {"package.whl", "package.tar.gz"}
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
        ("select", "draft"),
        ("publish", "select"),
    ):
        assert jobs[job]["needs"] == dependency
    for name, job in jobs.items():
        permissions = job.get("permissions", {})
        assert (permissions.get("contents") == "write") == (name in ("draft", "publish"))
        assert (permissions.get("id-token") == "write") == (name == "publish")
        for step in job.get("steps", []):
            if "uses" in step:
                assert len(step["uses"].split("@")[1]) == 40
    assert jobs["publish"]["environment"]["name"] == "pypi"
    assert not any("scripts/" in step.get("run", "") for step in jobs["publish"]["steps"])
    steps = jobs["publish"]["steps"]
    assert "gh release edit" in steps[-2]["run"]
    assert "pypa/gh-action-pypi-publish@" in steps[-1]["uses"]
    assert not any("checkout" in step.get("uses", "") for step in jobs["publish"]["steps"])
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
