import tomllib
from importlib.metadata import version
from pathlib import Path

import hayate_htmx

ROOT = Path(__file__).resolve().parents[1]


def test_distribution_and_public_versions_match() -> None:
    assert version("hayate-htmx") == hayate_htmx.__version__


def test_readme_release_state_matches_package() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert project["version"] == hayate_htmx.__version__
    assert f"source version `{project['version']}`" in readme
    assert "https://github.com/hayatepy/hayate-htmx/issues/7" in readme


def test_public_discovery_uses_the_canonical_site() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert project["urls"]["Homepage"] == "https://hayatepy.dev/ecosystem/#hayate-htmx"
    assert "[Start here](https://hayatepy.dev/)" in readme
    assert "[Tested compatibility](https://hayatepy.dev/evidence/compatibility/)" in readme
    assert "create-hayate==0.13.2" in readme
    assert "https://github.com/hayatepy/.github/blob/main/docs/" not in readme
