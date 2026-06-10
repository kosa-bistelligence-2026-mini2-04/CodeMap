"""SCIP Language Definitions.

This module defines all languages that have SCIP indexer implementations,
their implementation status in Cicada, and metadata for test generation.

SCIP Languages Reference:
- https://github.com/sourcegraph/scip
- https://scip.dev/
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ImplementationStatus(Enum):
    """Status of language implementation in Cicada."""

    IMPLEMENTED = "implemented"  # Fully working
    PARTIAL = "partial"  # Some features work
    PLANNED = "planned"  # Not yet implemented
    NOT_STARTED = "not_started"  # No work done


@dataclass
class SCIPLanguage:
    """Definition of a SCIP-supported language."""

    # Core identification
    name: str
    display_name: str
    file_extensions: list[str]

    # SCIP tooling
    scip_indexer: str  # e.g., "scip-python", "rust-analyzer"
    scip_indexer_repo: str  # GitHub URL

    # Cicada implementation status
    status: ImplementationStatus
    cicada_indexer_class: Optional[str] = None
    cicada_formatter_class: Optional[str] = None

    # Fixture information
    fixture_dir: Optional[str] = None  # e.g., "sample_python"
    sample_class_name: str = "Calculator"  # Standard class for testing

    # Additional metadata
    build_tool: Optional[str] = None  # e.g., "pip", "cargo", "npm"
    config_file: Optional[str] = None  # e.g., "pyproject.toml", "Cargo.toml"

    # Notes about implementation
    notes: list[str] = field(default_factory=list)

    @property
    def is_implemented(self) -> bool:
        """Check if language is implemented in Cicada."""
        return self.status == ImplementationStatus.IMPLEMENTED

    @property
    def fixture_path(self) -> Optional[Path]:
        """Get fixture path if defined."""
        if self.fixture_dir:
            return Path(__file__).parent.parent.parent / "fixtures" / self.fixture_dir
        return None


# =============================================================================
# SCIP Language Registry
# =============================================================================

SCIP_LANGUAGES: dict[str, SCIPLanguage] = {
    # =========================================================================
    # IMPLEMENTED LANGUAGES (tests should PASS)
    # =========================================================================
    "python": SCIPLanguage(
        name="python",
        display_name="Python",
        file_extensions=[".py"],  # Note: .pyi stubs indexed separately
        scip_indexer="scip-python",
        scip_indexer_repo="https://github.com/sourcegraph/scip-python",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.python.indexer.PythonSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.PythonFormatter",
        fixture_dir="sample_python",
        build_tool="pip/uv",
        config_file="pyproject.toml",
    ),
    "typescript": SCIPLanguage(
        name="typescript",
        display_name="TypeScript",
        file_extensions=[".ts", ".tsx"],
        scip_indexer="scip-typescript",
        scip_indexer_repo="https://github.com/sourcegraph/scip-typescript",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.typescript.indexer.TypeScriptSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.TypeScriptFormatter",
        fixture_dir="sample_typescript",
        build_tool="npm",
        config_file="package.json",
    ),
    "javascript": SCIPLanguage(
        name="javascript",
        display_name="JavaScript",
        file_extensions=[".js", ".jsx", ".mjs", ".cjs"],
        scip_indexer="scip-typescript",  # Uses same indexer as TypeScript
        scip_indexer_repo="https://github.com/sourcegraph/scip-typescript",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.typescript.indexer.JavaScriptSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.JavaScriptFormatter",
        fixture_dir="sample_typescript",  # Shares fixture with TypeScript
        build_tool="npm",
        config_file="package.json",
        notes=["Uses scip-typescript indexer", "Shares fixture with TypeScript"],
    ),
    "rust": SCIPLanguage(
        name="rust",
        display_name="Rust",
        file_extensions=[".rs"],
        scip_indexer="rust-analyzer",
        scip_indexer_repo="https://github.com/rust-lang/rust-analyzer",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.rust.indexer.RustSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.RustFormatter",
        fixture_dir="sample_rust",
        build_tool="cargo",
        config_file="Cargo.toml",
    ),
    # =========================================================================
    # OTHER IMPLEMENTED LANGUAGES
    # =========================================================================
    "go": SCIPLanguage(
        name="go",
        display_name="Go",
        file_extensions=[".go"],
        scip_indexer="scip-go",
        scip_indexer_repo="https://github.com/sourcegraph/scip-go",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.go.indexer.GoSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.GoFormatter",
        fixture_dir="sample_go",
        build_tool="go",
        config_file="go.mod",
        notes=["Go is a popular language with good SCIP support"],
    ),
    "java": SCIPLanguage(
        name="java",
        display_name="Java",
        file_extensions=[".java"],
        scip_indexer="scip-java",
        scip_indexer_repo="https://github.com/sourcegraph/scip-java",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.jvm.indexer.JavaSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.JavaFormatter",
        fixture_dir="sample_java",
        build_tool="gradle/maven",
        config_file="build.gradle",
        notes=["Also supports Scala through scip-java"],
    ),
    "scala": SCIPLanguage(
        name="scala",
        display_name="Scala",
        file_extensions=[".scala", ".sc"],
        scip_indexer="scip-java",  # Uses scip-java
        scip_indexer_repo="https://github.com/sourcegraph/scip-java",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.jvm.indexer.ScalaSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.ScalaFormatter",
        fixture_dir="sample_scala",
        build_tool="sbt",
        config_file="build.sbt",
        notes=["Uses scip-java indexer", "JVM language"],
    ),
    "c": SCIPLanguage(
        name="c",
        display_name="C",
        file_extensions=[".c", ".h"],
        scip_indexer="scip-clang",
        scip_indexer_repo="https://github.com/sourcegraph/scip-clang",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.clang.indexer.CSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.CFormatter",
        fixture_dir="sample_c",
        build_tool="make/cmake",
        config_file="Makefile",
        notes=["Uses scip-clang indexer"],
    ),
    "cpp": SCIPLanguage(
        name="cpp",
        display_name="C++",
        file_extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"],
        scip_indexer="scip-clang",
        scip_indexer_repo="https://github.com/sourcegraph/scip-clang",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.clang.indexer.CppSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.CppFormatter",
        fixture_dir="sample_cpp",
        build_tool="cmake",
        config_file="CMakeLists.txt",
        notes=["Uses scip-clang indexer", "Also supports CUDA"],
    ),
    "ruby": SCIPLanguage(
        name="ruby",
        display_name="Ruby",
        file_extensions=[".rb", ".rake"],
        scip_indexer="scip-ruby",
        scip_indexer_repo="https://github.com/sourcegraph/scip-ruby",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.ruby.indexer.RubySCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.RubyFormatter",
        fixture_dir="sample_ruby",
        build_tool="bundler",
        config_file="Gemfile",
    ),
    "csharp": SCIPLanguage(
        name="csharp",
        display_name="C#",
        file_extensions=[".cs"],
        scip_indexer="scip-dotnet",
        scip_indexer_repo="https://github.com/sourcegraph/scip-dotnet",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.dotnet.indexer.CSharpSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.CSharpFormatter",
        fixture_dir="sample_csharp",
        build_tool="dotnet",
        config_file="*.csproj",
        notes=["Uses scip-dotnet indexer", "Also supports Visual Basic"],
    ),
    "vb": SCIPLanguage(
        name="vb",
        display_name="Visual Basic",
        file_extensions=[".vb"],
        scip_indexer="scip-dotnet",
        scip_indexer_repo="https://github.com/sourcegraph/scip-dotnet",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.dotnet.indexer.VBSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.VBFormatter",
        fixture_dir="sample_vb",
        build_tool="dotnet",
        config_file="*.vbproj",
        notes=["Uses scip-dotnet indexer"],
    ),
    # =========================================================================
    # COMMUNITY/THIRD-PARTY LANGUAGES (also implemented)
    # =========================================================================
    "dart": SCIPLanguage(
        name="dart",
        display_name="Dart",
        file_extensions=[".dart"],
        scip_indexer="scip-dart",
        scip_indexer_repo="https://github.com/Workiva/scip-dart",
        status=ImplementationStatus.IMPLEMENTED,
        cicada_indexer_class="cicada.languages.dart.indexer.DartSCIPIndexer",
        cicada_formatter_class="cicada.languages.scip.formatter.DartFormatter",
        fixture_dir="sample_dart",
        build_tool="pub",
        config_file="pubspec.yaml",
        notes=["Community-maintained by Workiva"],
    ),
}


def get_implemented_languages() -> list[SCIPLanguage]:
    """Get all languages that are implemented in Cicada."""
    return [lang for lang in SCIP_LANGUAGES.values() if lang.is_implemented]


def get_unimplemented_languages() -> list[SCIPLanguage]:
    """Get all languages that are NOT implemented in Cicada."""
    return [lang for lang in SCIP_LANGUAGES.values() if not lang.is_implemented]


def get_all_languages() -> list[SCIPLanguage]:
    """Get all SCIP languages."""
    return list(SCIP_LANGUAGES.values())


def get_language(name: str) -> Optional[SCIPLanguage]:
    """Get a language by name."""
    return SCIP_LANGUAGES.get(name)


# =============================================================================
# Test Feature Definitions
# =============================================================================


class SCIPFeature(Enum):
    """Features that can be tested across SCIP languages."""

    # Core structure
    INDEX_STRUCTURE = "index_structure"  # Has modules and metadata
    MODULE_EXTRACTION = "module_extraction"  # Extracts classes/modules
    FUNCTION_EXTRACTION = "function_extraction"  # Extracts functions/methods
    LINE_NUMBERS = "line_numbers"  # Accurate line number tracking

    # Type information
    PUBLIC_PRIVATE = "public_private"  # Distinguishes visibility
    ARITY = "arity"  # Function parameter count
    SIGNATURES = "signatures"  # Function signature extraction
    TYPE_ANNOTATIONS = "type_annotations"  # Type hint extraction

    # Documentation
    DOCSTRINGS = "docstrings"  # Extracts documentation
    MODULE_DOCS = "module_docs"  # Module-level documentation

    # Cross-reference
    REFERENCES = "references"  # Symbol reference tracking
    DEPENDENCIES = "dependencies"  # Module dependency tracking

    # Advanced
    KEYWORDS = "keywords"  # Keyword extraction from code
    SCHEMA_VALIDATION = "schema_validation"  # Validates against schema


# Features expected to work for all implemented languages
CORE_FEATURES = [
    SCIPFeature.INDEX_STRUCTURE,
    SCIPFeature.MODULE_EXTRACTION,
    SCIPFeature.FUNCTION_EXTRACTION,
    SCIPFeature.LINE_NUMBERS,
    SCIPFeature.PUBLIC_PRIVATE,
    SCIPFeature.ARITY,
]

# Features that may vary by language
OPTIONAL_FEATURES = [
    SCIPFeature.SIGNATURES,
    SCIPFeature.TYPE_ANNOTATIONS,
    SCIPFeature.DOCSTRINGS,
    SCIPFeature.MODULE_DOCS,
    SCIPFeature.REFERENCES,
    SCIPFeature.DEPENDENCIES,
    SCIPFeature.KEYWORDS,
    SCIPFeature.SCHEMA_VALIDATION,
]


__all__ = [
    "SCIPLanguage",
    "ImplementationStatus",
    "SCIPFeature",
    "SCIP_LANGUAGES",
    "CORE_FEATURES",
    "OPTIONAL_FEATURES",
    "get_implemented_languages",
    "get_unimplemented_languages",
    "get_all_languages",
    "get_language",
]
