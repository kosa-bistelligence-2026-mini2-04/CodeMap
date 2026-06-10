"""Shared pytest fixtures. Everything here is offline and deterministic.

The default embedding provider for tests is the ``fake`` provider, so the suite never
downloads a model or touches the network. Real backends are exercised only by tests
marked ``@pytest.mark.integration`` (deselected in CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from coderag.config import Config


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """A fake-provider config rooted at an isolated tmp dir."""
    return Config(
        provider="fake",
        watched_dir=tmp_path / "repo",
        store_dir=tmp_path / "store",
        ivf_threshold=20,  # tiny so IVF-path tests don't need huge corpora
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An empty repo directory under tmp."""
    d = tmp_path / "repo"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
