"""P6 tests: CLI, HTTP API, and watcher behaviour (all with the fake provider)."""

from __future__ import annotations

import json

import pytest

from coderag.api import CodeRAG
from coderag.surfaces.cli import main as cli_main
from tests.conftest import write


@pytest.fixture
def repo_with_code(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    store = tmp_path / "store"
    write(repo / "auth.py", "def authenticate(token):\n    return token == 'ok'\n")
    monkeypatch.setenv("CODERAG_PROVIDER", "fake")
    common = ["--watched-dir", str(repo), "--store-dir", str(store)]
    return repo, store, common


# --- CLI ---


def test_cli_index_then_search(repo_with_code, capsys):
    repo, store, common = repo_with_code
    assert cli_main(["index", "--quiet", *common]) == 0
    assert "Indexed" in capsys.readouterr().out

    assert cli_main(["search", "authenticate", "-k", "3", *common]) == 0
    out = capsys.readouterr().out
    assert "auth.py:1" in out


def test_cli_search_json(repo_with_code, capsys):
    repo, store, common = repo_with_code
    cli_main(["index", "--quiet", *common])
    capsys.readouterr()
    rc = cli_main(["search", "authenticate", "--json", *common])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload[0]["path"] == "auth.py"


def test_cli_status(repo_with_code, capsys):
    repo, store, common = repo_with_code
    cli_main(["index", "--quiet", *common])
    capsys.readouterr()
    cli_main(["status", *common])
    status = json.loads(capsys.readouterr().out)
    assert status["provider"] == "fake"
    assert status["total_files"] == 1


def test_cli_search_without_index(repo_with_code, capsys):
    repo, store, common = repo_with_code
    rc = cli_main(["search", "anything", *common])
    assert rc == 1
    assert "No results" in capsys.readouterr().out


# --- HTTP API ---


def test_http_api_search_and_status(repo_with_code):
    from fastapi.testclient import TestClient

    from coderag.surfaces.http_api import create_app

    repo, store, _ = repo_with_code
    from coderag.config import Config

    cr = CodeRAG(Config(provider="fake", watched_dir=repo, store_dir=store))
    cr.index()
    client = TestClient(create_app(cr))

    r = client.get("/status")
    assert r.status_code == 200
    assert r.json()["total_files"] == 1

    r = client.get("/search", params={"q": "authenticate", "k": 3})
    body = r.json()
    assert body["count"] >= 1
    assert body["results"][0]["path"] == "auth.py"

    r = client.get("/file", params={"path": "auth.py"})
    assert "authenticate" in r.json()["content"]

    r = client.get("/file", params={"path": "../../etc/passwd"})
    assert r.status_code == 404  # path traversal blocked


def test_http_index_endpoint(repo_with_code):
    from fastapi.testclient import TestClient

    from coderag.config import Config
    from coderag.surfaces.http_api import create_app

    repo, store, _ = repo_with_code
    cr = CodeRAG(Config(provider="fake", watched_dir=repo, store_dir=store))
    client = TestClient(create_app(cr))
    r = client.post("/index", json={"full": False})
    assert r.status_code == 200
    assert r.json()["total_files"] == 1


# --- watcher ---


def test_watcher_apply_handles_edit_and_delete(repo_with_code):
    from coderag.config import Config
    from coderag.watch import _apply

    repo, store, _ = repo_with_code
    cr = CodeRAG(Config(provider="fake", watched_dir=repo, store_dir=store))
    cr.index()
    n0 = cr.store.total_chunks()

    new = repo / "extra.py"
    write(new, "def extra():\n    return 1\n")
    _apply(cr, str(new))
    assert cr.store.total_chunks() > n0
    assert cr.store.total_chunks() == cr.vectors.ntotal

    new.unlink()
    _apply(cr, str(new))
    assert "extra.py" not in cr.store.all_file_paths()
    assert cr.store.total_chunks() == cr.vectors.ntotal
