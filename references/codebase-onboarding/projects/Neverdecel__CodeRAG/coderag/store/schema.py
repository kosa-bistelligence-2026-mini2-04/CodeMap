"""SQLite schema for the CodeRAG store.

Design notes:
- ``chunks.id`` IS the FAISS id. It is ``AUTOINCREMENT`` so ids are *never reused*, which
  is what keeps a stale FAISS cache from resurrecting deleted content under a recycled id.
- ``chunks_fts`` is an external-content FTS5 table (no duplicated text) kept in sync by
  triggers, giving us BM25 lexical search for free alongside dense vectors.
- ``files.content_hash`` drives incremental indexing; ``meta`` records the embedding
  model/dim so a provider switch can trigger a rebuild instead of crashing.
"""

from __future__ import annotations

SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT NOT NULL UNIQUE,
    language     TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    mtime        REAL,
    indexed_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);

CREATE TABLE IF NOT EXISTS chunks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id        INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    symbol         TEXT,
    kind           TEXT NOT NULL DEFAULT 'window',
    start_line     INTEGER NOT NULL,
    end_line       INTEGER NOT NULL,
    language       TEXT NOT NULL,
    text           TEXT NOT NULL,
    vector         BLOB NOT NULL,
    embed_model    TEXT NOT NULL,
    created_at     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    symbol,
    content='chunks',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, symbol) VALUES (new.id, new.text, new.symbol);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, symbol)
        VALUES('delete', old.id, old.text, old.symbol);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, symbol)
        VALUES('delete', old.id, old.text, old.symbol);
    INSERT INTO chunks_fts(rowid, text, symbol) VALUES (new.id, new.text, new.symbol);
END;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""
