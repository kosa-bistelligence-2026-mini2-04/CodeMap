from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.static_analyzer import (
    StaticAnalyzer,
    _cc_to_risk_level,
    _collect_python_files,
    _merge_heatmaps,
    _run_pylint,
    _run_radon,
)
from app.models.agent_schemas import (
    LineRisk,
    RiskLevel,
    StaticAnalyzerInput,
)

TINY_REPO = Path(__file__).parent / "fixtures" / "tiny_repo"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(**kwargs) -> StaticAnalyzerInput:
    defaults = dict(
        repo_path=str(TINY_REPO),
        job_id="test-job-001",
        timeout_seconds=60,
        pylint_threshold=7.0,
        cc_threshold=10,
        coverage_threshold=70.0,
    )
    defaults.update(kwargs)
    return StaticAnalyzerInput(**defaults)


# ---------------------------------------------------------------------------
# test_pylint_subprocess_no_shell
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pylint_subprocess_no_shell():
    """create_subprocess_exec must never be called with shell=True."""
    captured_kwargs: dict = {}

    async def fake_proc_communicate():
        return b"[]", b""

    fake_proc = MagicMock()
    fake_proc.communicate = AsyncMock(return_value=(b"[]", b""))

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
        await _run_pylint(str(TINY_REPO), ["simple.py"], 7.0)

    assert captured_kwargs.get("shell") is not True, (
        "create_subprocess_exec must NOT be called with shell=True"
    )


# ---------------------------------------------------------------------------
# test_radon_cc_mapping
# ---------------------------------------------------------------------------

def test_radon_cc_mapping():
    """CC values must map to the correct RiskLevel buckets."""
    assert _cc_to_risk_level(1) == RiskLevel.LOW
    assert _cc_to_risk_level(3) == RiskLevel.LOW
    assert _cc_to_risk_level(5) == RiskLevel.LOW
    assert _cc_to_risk_level(6) == RiskLevel.MEDIUM
    assert _cc_to_risk_level(10) == RiskLevel.MEDIUM
    assert _cc_to_risk_level(11) == RiskLevel.HIGH
    assert _cc_to_risk_level(12) == RiskLevel.HIGH
    assert _cc_to_risk_level(15) == RiskLevel.HIGH
    assert _cc_to_risk_level(16) == RiskLevel.CRITICAL
    assert _cc_to_risk_level(20) == RiskLevel.CRITICAL
    assert _cc_to_risk_level(100) == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# test_skip_test_directories
# ---------------------------------------------------------------------------

def test_skip_test_directories():
    """Files under tests/ subdirectories must not appear in the collected list."""
    python_files = _collect_python_files(str(TINY_REPO))
    for f in python_files:
        parts = Path(f).parts
        assert "tests" not in parts, (
            f"File '{f}' is inside a tests/ directory and should have been skipped"
        )
        assert not Path(f).name.startswith("test_"), (
            f"File '{f}' matches test_* pattern and should have been skipped"
        )


# ---------------------------------------------------------------------------
# test_budget_timeout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_budget_timeout_degrades_gracefully():
    """pylint subprocess that hangs must degrade to empty dict (not raise).

    Design change: on large repos (150+ files) pylint regularly exceeds its
    budget. Instead of aborting the entire pipeline into emergency mode, we
    let radon still provide CC data and return an empty pylint score dict.
    """
    async def hanging_communicate():
        await asyncio.sleep(9999)
        return b"", b""

    fake_proc = MagicMock()
    fake_proc.communicate = hanging_communicate

    async def fake_create_subprocess_exec(*args, **kwargs):
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
        with patch("app.agents.static_analyzer._PYLINT_BUDGET", 0.05):
            result = await _run_pylint(str(TINY_REPO), ["simple.py"], 7.0)
            assert result == {}


# ---------------------------------------------------------------------------
# test_file_heatmap_merge
# ---------------------------------------------------------------------------

def test_file_heatmap_merge():
    """Merged heatmap must use the highest RiskLevel when both sources cover the same line."""
    radon_heatmap = {
        "analyzer.py": [
            LineRisk(line=10, risk_level=RiskLevel.HIGH, reason="High CC=12"),
        ]
    }
    coverage_heatmap = {
        "analyzer.py": [
            LineRisk(line=10, risk_level=RiskLevel.MEDIUM, reason="Uncovered by tests"),
            LineRisk(line=20, risk_level=RiskLevel.MEDIUM, reason="Uncovered by tests"),
        ]
    }

    merged = _merge_heatmaps(radon_heatmap, coverage_heatmap)

    assert "analyzer.py" in merged
    by_line = {e.line: e for e in merged["analyzer.py"]}

    # Line 10: radon HIGH vs coverage MEDIUM → should be HIGH
    assert by_line[10].risk_level == RiskLevel.HIGH, (
        "Line 10 should retain HIGH (radon) over MEDIUM (coverage)"
    )
    # Line 20: only in coverage → MEDIUM
    assert by_line[20].risk_level == RiskLevel.MEDIUM


def test_file_heatmap_merge_critical_wins():
    """CRITICAL from coverage must override HIGH from radon."""
    radon_heatmap = {
        "god_object.py": [
            LineRisk(line=5, risk_level=RiskLevel.HIGH, reason="CC=12"),
        ]
    }
    coverage_heatmap = {
        "god_object.py": [
            LineRisk(line=5, risk_level=RiskLevel.CRITICAL, reason="Uncovered critical path"),
        ]
    }

    merged = _merge_heatmaps(radon_heatmap, coverage_heatmap)
    by_line = {e.line: e for e in merged["god_object.py"]}
    assert by_line[5].risk_level == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# test_collect_python_files_excludes_pyc
# ---------------------------------------------------------------------------

def test_collect_python_files_excludes_venv(tmp_path: Path):
    """Files under venv/ must be excluded."""
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "site.py").write_text("x = 1")
    (tmp_path / "main.py").write_text("x = 1")

    files = _collect_python_files(str(tmp_path))
    assert not any("venv" in f for f in files), "venv/ files should be excluded"
    assert any("main.py" in f for f in files), "main.py should be included"


# ---------------------------------------------------------------------------
# test_radon_subprocess_no_shell
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_radon_subprocess_no_shell():
    """radon subprocess must not use shell=True."""
    captured_kwargs: dict = {}
    fake_proc = MagicMock()
    fake_proc.communicate = AsyncMock(return_value=(b"{}", b""))

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
        await _run_radon(str(TINY_REPO), 10)

    assert captured_kwargs.get("shell") is not True


# ---------------------------------------------------------------------------
# test_full_run_with_mocked_subprocesses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_run_with_mocked_subprocesses(tmp_path: Path):
    """Full StaticAnalyzer.run with mocked pylint+radon returns valid StaticResult."""
    (tmp_path / "module_a.py").write_text("def foo(): pass\n")

    radon_output = json.dumps({
        str(tmp_path / "module_a.py"): [
            {"name": "foo", "complexity": 12, "lineno": 1}
        ]
    }).encode()

    pylint_output = b"[]"

    call_count = 0

    async def fake_create_subprocess_exec(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        fake_proc = MagicMock()
        if "pylint" in args:
            fake_proc.communicate = AsyncMock(return_value=(pylint_output, b""))
        else:
            fake_proc.communicate = AsyncMock(return_value=(radon_output, b""))
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
        analyzer = StaticAnalyzer()
        result = await analyzer.run(
            StaticAnalyzerInput(
                repo_path=str(tmp_path),
                job_id="full-run-test",
                timeout_seconds=60,
                pylint_threshold=7.0,
                cc_threshold=10,
                coverage_threshold=70.0,
            )
        )

    assert result.job_id == "full-run-test"
    assert result.total_files_scanned >= 1
    assert len(result.high_complexity_functions) == 1
    assert result.high_complexity_functions[0].cc == 12
    assert result.high_complexity_functions[0].risk_level == RiskLevel.HIGH
    assert result.duration_ms >= 0
