"""Rust language support for Cicada.

This module provides SCIP-based indexing for Rust projects using rust-analyzer.
"""

from cicada.languages.rust.indexer import RustSCIPIndexer
from cicada.languages.rust.symbol_types import get_symbol_type, is_callable

__all__ = ["RustSCIPIndexer", "get_symbol_type", "is_callable"]
