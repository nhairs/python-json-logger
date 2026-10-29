"""Release policy unit tests and local file/Git checks; no remote API simulations."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

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
    directory = distributions(tmp_path)
    release.validate_distributions(directory, "4.3.0")
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


@pytest.mark.parametrize("reachable", [True, False])
def test_prepare_with_real_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reachable: bool
) -> None:
    repository = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", str(ROOT), str(repository)], check=True
    )
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "-C", str(repository), "checkout", "--detach", head], check=True)
    monkeypatch.chdir(repository)
    base = head if reachable else head + "^"
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", base], check=True)
    Path("pyproject.toml").write_text('[project]\nversion = "4.3.0"\n')
    Path("docs/changelog.md").write_text(changelog())
    target = repository / "bundle"
    if reachable:
        release.prepare("v4.3.0", target)
        assert json.loads((target / "release.json").read_text())["commit"] == head
        assert (target / "notes.md").read_text().startswith("## [4.3.0]")
    else:
        with pytest.raises(subprocess.CalledProcessError):
            release.prepare("v4.3.0", target)
        assert not target.exists()
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


@pytest.mark.parametrize("change_date", [False, True])
def test_postrelease_date_against_base_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change_date: bool
) -> None:
    repository = tmp_path / "repo"
    subprocess.run(["git", "clone", "--shared", str(ROOT), str(repository)], check=True)
    monkeypatch.chdir(repository)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    original = subprocess.check_output(
        ["git", "show", "refs/tags/v4.2.0:docs/changelog.md"], text=True
    )
    _, original_notes = release.release_info("v4.2.0", "4.2.0", original)
    original_date = original_notes.split("\n", 1)[0].rsplit(" - ", 1)[1]
    text = changelog("2000-01-01" if change_date else original_date).replace("[4.3.0]", "[4.2.0]")
    # Keep just the first section: the generic fixture already has an older 4.2.0 entry.
    text = text.split("## [4.2.0]", 2)
    Path("docs/changelog.md").write_text(text[0] + "## [4.2.0]" + text[1])
    Path("pyproject.toml").write_text('[project]\nversion = "4.2.0.post1"\n')
    target = repository / "bundle"
    if change_date:
        with pytest.raises(ValueError, match="retain the base release date"):
            release.prepare("v4.2.0.post1", target)
        assert not target.exists()
    else:
        release.prepare("v4.2.0.post1", target)
        assert original_date in (target / "notes.md").read_text().split("\n", 1)[0]
    return None
