"""
Pytest configuration and fixtures for SCIP tests.
"""

from pathlib import Path

import pytest

# tests/languages/scip/ -> tests/
TESTS_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """Mock the home directory for storage tests"""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def python_scip_index():
    """Fixture that provides a pre-generated Python SCIP index for testing."""
    fixture_path = TESTS_ROOT / "fixtures" / "sample_python" / "index.scip"
    if not fixture_path.exists():
        pytest.skip("Python SCIP index not found - run make setup-scip")
    return fixture_path


@pytest.fixture
def typescript_scip_index():
    """Fixture that provides a pre-generated TypeScript SCIP index for testing."""
    fixture_path = TESTS_ROOT / "fixtures" / "sample_typescript" / "index.scip"
    if not fixture_path.exists():
        pytest.skip("TypeScript SCIP index not found - run make setup-scip")
    return fixture_path


@pytest.fixture
def sample_python_fixture_path():
    """Path to sample Python fixture directory."""
    return TESTS_ROOT / "fixtures" / "sample_python"


@pytest.fixture
def sample_typescript_fixture_path():
    """Path to sample TypeScript fixture directory."""
    return TESTS_ROOT / "fixtures" / "sample_typescript"
