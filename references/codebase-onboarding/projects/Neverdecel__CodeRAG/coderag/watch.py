"""Debounced filesystem watcher that keeps the index live as files change.

Replaces the old ``monitor.py``. Two important differences: events are *debounced* (editors
fire several writes per save) and each flushed path is re-hashed by the indexer, so an
unchanged file costs nothing and a changed file is updated without duplicating vectors.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from coderag.chunking.languages import detect_language

if TYPE_CHECKING:
    from coderag.api import CodeRAG

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, pending: Set[str], lock: threading.Lock) -> None:
        self._pending = pending
        self._lock = lock

    def _note(self, path: str) -> None:
        if path and detect_language(path):
            with self._lock:
                self._pending.add(path)

    def on_modified(self, event):
        if not event.is_directory:
            self._note(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._note(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._note(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._note(event.src_path)
            self._note(getattr(event, "dest_path", ""))


def watch(cr: "CodeRAG", debounce: float = 0.5) -> None:
    """Block, keeping ``cr``'s index in sync with its watched directory until Ctrl-C."""
    root = cr.config.watched_dir
    pending: Set[str] = set()
    lock = threading.Lock()
    handler = _Handler(pending, lock)
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    logger.info("Watching %s for changes (Ctrl-C to stop)...", root)

    try:
        while True:
            time.sleep(debounce)
            with lock:
                batch = set(pending)
                pending.clear()
            for raw in batch:
                _apply(cr, raw)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
    finally:
        observer.stop()
        observer.join()


def _apply(cr: "CodeRAG", raw: str) -> None:
    path = Path(raw)
    try:
        if path.exists():
            stats = cr.index(path)
            if stats.files_indexed:
                logger.info("Reindexed %s (+%d chunks)", raw, stats.chunks_added)
        else:
            removed = cr.delete_path(path)
            if removed:
                logger.info("Removed %s (-%d chunks)", raw, removed)
    except Exception as exc:  # pragma: no cover - defensive, keep the loop alive
        logger.error("Failed to process %s: %s", raw, exc)
