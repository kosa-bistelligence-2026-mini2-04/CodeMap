"""Tests for template documentation completeness."""

import json
import re
from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).parent.parent / "template"


class TestVariablesDocumentation:
    """Tests for VARIABLES.md documentation."""

    @pytest.fixture
    def cookiecutter_variables(self) -> set[str]:
        """Load all variable names from cookiecutter.json.

        Excludes variables starting with '_' as these are internal/private
        cookiecutter variables not meant for user documentation.
        """
        cookiecutter_json = TEMPLATE_DIR / "cookiecutter.json"
        with cookiecutter_json.open() as f:
            data = json.load(f)
        # Exclude private variables (prefixed with _)
        return {k for k in data if not k.startswith("_")}

    @pytest.fixture
    def documented_variables(self) -> set[str]:
        """Extract all variable names documented in VARIABLES.md."""
        variables_md = TEMPLATE_DIR / "VARIABLES.md"
        content = variables_md.read_text()

        # Match variables in first column of markdown tables: | `variable_name` |
        # The variable name must contain at least one underscore or be a known variable
        pattern = r"^\| `([a-z][a-z0-9_]+)` \|"
        matches = re.findall(pattern, content, re.MULTILINE)
        return set(matches)

    def test_variables_md_exists(self) -> None:
        """Test that VARIABLES.md exists."""
        variables_md = TEMPLATE_DIR / "VARIABLES.md"
        assert variables_md.exists(), "VARIABLES.md not found in template directory"

    def test_all_variables_documented(
        self, cookiecutter_variables: set[str], documented_variables: set[str]
    ) -> None:
        """Test that all cookiecutter.json variables are documented."""
        undocumented = cookiecutter_variables - documented_variables

        assert not undocumented, (
            f"The following variables are not documented in VARIABLES.md:\n{sorted(undocumented)}"
        )

    def test_no_stale_documentation(
        self, cookiecutter_variables: set[str], documented_variables: set[str]
    ) -> None:
        """Test that VARIABLES.md doesn't document non-existent variables."""
        stale = documented_variables - cookiecutter_variables

        assert not stale, (
            f"The following documented variables don't exist in cookiecutter.json:\n{sorted(stale)}"
        )

    def test_documentation_has_required_sections(self) -> None:
        """Test that VARIABLES.md has all required sections."""
        variables_md = TEMPLATE_DIR / "VARIABLES.md"
        content = variables_md.read_text()

        required_sections = [
            "## Project Information",
            "## Database Settings",
            "## Authentication",
            "## Observability (Logfire)",
            "## Background Tasks",
            "## Features",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"
