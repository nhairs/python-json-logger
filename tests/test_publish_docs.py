"""Check routing of public documentation versions."""

from pathlib import Path
import runpy

import pytest

pytest.importorskip("tomllib", reason="Documentation publishing uses Python 3.12")

PUBLISH = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "publish_docs.py"))


@pytest.mark.parametrize(
    "value,label,stable",
    [
        ("4.3.0", "4.3.0", True),
        ("4.3.0.post1", "4.3.0", True),
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
