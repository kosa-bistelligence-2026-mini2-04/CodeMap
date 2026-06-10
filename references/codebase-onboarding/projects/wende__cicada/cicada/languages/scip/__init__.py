"""SCIP support for Cicada.

SCIP is a language-agnostic protocol created by Sourcegraph for code intelligence.
Learn more: https://github.com/sourcegraph/scip
"""

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import (
    SCIPConverter,
    CallSite,
    DocumentData,
    ImportData,
    SymbolData,
)
from cicada.languages.scip.formatter import (
    CFormatter,
    CppFormatter,
    CSharpFormatter,
    DartFormatter,
    GoFormatter,
    JavaFormatter,
    JavaScriptFormatter,
    PythonFormatter,
    RubyFormatter,
    RustFormatter,
    ScalaFormatter,
    SCIPFormatter,
    TypeScriptFormatter,
    VBFormatter,
)
from cicada.languages.scip.indexer import GenericSCIPIndexer

import cicada.languages.scip.scip_pb2 as scip_pb2

SCIP_AVAILABLE = True
SCIP_IMPORT_ERROR = None

__all__ = [
    "SCIPReader",
    "SCIPConverter",
    "GenericSCIPIndexer",
    "DocumentData",
    "SymbolData",
    "CallSite",
    "ImportData",
    "SCIPFormatter",
    "PythonFormatter",
    "TypeScriptFormatter",
    "JavaScriptFormatter",
    "GoFormatter",
    "RustFormatter",
    "JavaFormatter",
    "ScalaFormatter",
    "CFormatter",
    "CppFormatter",
    "CSharpFormatter",
    "VBFormatter",
    "RubyFormatter",
    "DartFormatter",
    "scip_pb2",
    "SCIP_AVAILABLE",
    "SCIP_IMPORT_ERROR",
]
