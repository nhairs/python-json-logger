"""Exercise documentation publishing against a disposable local Git remote."""

import json
import subprocess
import sys
from pathlib import Path
import runpy

import pytest

pytest.importorskip("tomllib", reason="Documentation publishing uses Python 3.12")

PUBLISH = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "publish_docs.py"))


@pytest.mark.parametrize(
    "value,label,stable",
    [
        ("4.3.0", "4.3.0", True),
        ("4.3.0.post1", "4.3.0.post1", True),
        ("4.3.0.dev1", "dev", False),
        ("4.3.0a1", "dev", False),
        ("4.3.0b1", "dev", False),
        ("4.3.0rc1", "dev", False),
    ],
)
def test_version_routing(value: str, label: str, stable: bool) -> None:
    assert PUBLISH["documentation_version"](value) == (label, stable)


@pytest.mark.parametrize("value", ["invalid", "4.3.0+local"])
def test_invalid_public_version(value: str) -> None:
    with pytest.raises(ValueError):
        PUBLISH["documentation_version"](value)


@pytest.mark.skipif(sys.platform == "win32", reason="Publishing runs on Ubuntu")
def test_mike_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Build locally, preserve old releases, and push only complete transitions."""
    remote = tmp_path / "remote.git"
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(checkout)], check=True, capture_output=True)
    monkeypatch.chdir(checkout)

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], text=True).strip()

    git("config", "user.name", "Documentation test")
    git("config", "user.email", "docs-test@example.invalid")
    Path("docs").mkdir()
    Path("docs/index.md").write_text("# Original documentation\n")
    Path("mkdocs.yml").write_text("site_name: Test\ntheme: material\nplugins: [search, mike]\n")
    Path("pyproject.toml").write_text('[project]\nversion = "4.2.0"\n')
    git("add", ".")
    git("commit", "-m", "Seed documentation")

    def publish(version: str) -> None:
        Path("pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
        PUBLISH["main"]()

    def versions() -> dict:
        return {item["version"]: item for item in json.loads(git("show", "gh-pages:versions.json"))}

    publish("4.2.0")  # Initial stable publication with no dev version.
    git("push", "origin", "gh-pages")
    original = git("rev-parse", "gh-pages:4.2.0")
    redirect = git("show", "gh-pages:index.html")
    remote_before = git("ls-remote", "origin", "refs/heads/gh-pages")
    for version in ["4.3.0.dev1", "4.3.0a1", "4.3.0b1", "4.3.0rc1"]:
        publish(version)
        assert set(versions()) == {"4.2.0", "dev"}
        assert versions()["4.2.0"]["aliases"] == ["latest"]
        assert git("show", "gh-pages:index.html") == redirect
    assert git("ls-remote", "origin", "refs/heads/gh-pages") == remote_before

    publish("4.3.0")
    publish("4.3.0")  # Repeated stable publication must be safe.
    assert set(versions()) == {"4.2.0", "4.3.0"}
    assert versions()["4.3.0"]["aliases"] == ["latest"]
    assert versions()["4.2.0"]["aliases"] == []
    assert git("rev-parse", "gh-pages:4.2.0") == original
    assert git("show", "gh-pages:latest") == "4.3.0"

    # A failed build must not delete dev or change the stable alias.
    publish("4.4.0.dev1")
    before = git("rev-parse", "gh-pages")
    Path("mkdocs.yml").write_text("site_name: Test\nplugins: [nonexistent-plugin]\n")
    with pytest.raises(subprocess.CalledProcessError):
        publish("4.4.0")
    assert git("rev-parse", "gh-pages") == before
    assert "dev" in versions()
    assert git("ls-remote", "origin", "refs/heads/gh-pages") == remote_before

    # Materialize the same tree that the workflow uploads, including latest.
    history = tmp_path / "history"
    stage = tmp_path / "pages"
    git("worktree", "add", "--detach", str(history), "gh-pages")
    subprocess.run(["cp", "-rL", str(history), str(stage)], check=True)
    (stage / ".git").unlink()
    assert not any(path.is_symlink() for path in stage.rglob("*"))
    assert not (stage / ".git").exists()
    assert (stage / "latest/index.html").read_bytes() == (stage / "4.3.0/index.html").read_bytes()
    assert (stage / "4.2.0/index.html").exists()
    assert (stage / "dev/index.html").exists()
    assert "latest/" in (stage / "index.html").read_text()

    # Rejected pushes leave the remote intact, and a retry can publish history.
    hook = remote / "hooks/pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    with pytest.raises(subprocess.CalledProcessError):
        git("push", "origin", "gh-pages")
    assert git("ls-remote", "origin", "refs/heads/gh-pages") == remote_before
    hook.unlink()
    git("push", "origin", "gh-pages")
    assert git("rev-parse", "gh-pages") in git("ls-remote", "origin", "refs/heads/gh-pages")
