import importlib
import importlib.metadata
import tomllib
from pathlib import Path

import pytest

import vietnamese_writing_skills
from vietnamese_writing_skills.cli import lint
from vietnamese_writing_skills.core.paths import data_location
from vietnamese_writing_skills.core.patterns import pattern_index

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_is_derived_from_distribution_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_version = "test-version-from-metadata"

    def metadata_version(distribution_name: str) -> str:
        assert distribution_name == "vietnamese-writing-skills"
        return expected_version

    try:
        with monkeypatch.context() as patch:
            patch.setattr(importlib.metadata, "version", metadata_version)
            reloaded_package = importlib.reload(vietnamese_writing_skills)
            assert reloaded_package.__version__ == expected_version
    finally:
        importlib.reload(vietnamese_writing_skills)


def test_console_entry_module_exposes_main() -> None:
    assert callable(lint.main)


def test_repository_resources_are_loaded() -> None:
    location = data_location("patterns", ROOT)
    assert len(pattern_index(location)) >= 43


def test_pyproject_packages_official_import_and_resources() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src/vietnamese_writing_skills"]' in pyproject
    assert '"patterns" = "vietnamese_writing_skills/data/patterns"' in pyproject


def test_release_metadata_matches_package_version() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert pyproject["build-system"]["requires"] == ["hatchling>=1.27,<1.32"]
    assert project["version"] == vietnamese_writing_skills.__version__
    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert "Programming Language :: Python :: 3.14" in project["classifiers"]
    assert "Natural Language :: Vietnamese" in project["classifiers"]
    assert project["urls"] == {
        "Homepage": "https://github.com/datnguyentien2006/vietnamese-humanize",
        "Repository": "https://github.com/datnguyentien2006/vietnamese-humanize",
        "Issues": "https://github.com/datnguyentien2006/vietnamese-humanize/issues",
    }
    assert list(project["scripts"]) == ["viet-writing-lint"]
