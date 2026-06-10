"""Tests for Rust symbol type detection."""

import pytest

from cicada.languages.rust.symbol_types import get_symbol_type, is_callable


class TestRustSymbolTypes:
    """Test Rust symbol type detection.

    Rust SCIP symbol patterns (from rust-analyzer):
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/Calculator# -> struct
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/Calculator#add(). -> method
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/helper_function(). -> function
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/operations/ -> module
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/Displayable# -> trait
    - rust-analyzer cargo sample_rust 0.1.0 sample_rust/OperationType# -> enum
    """

    def test_function_detection(self):
        """Rust functions end with ()."""
        assert get_symbol_type("sample_rust/helper_function().") == "function"
        assert get_symbol_type("sample_rust/operations/add().") == "function"

    def test_method_detection(self):
        """Rust methods contain # and end with ()."""
        assert get_symbol_type("sample_rust/Calculator#add().") == "method"
        assert get_symbol_type("sample_rust/Calculator#new().") == "method"
        # Trait method implementations
        assert get_symbol_type("sample_rust/Calculator#[Displayable]format().") == "method"

    def test_struct_detection(self):
        """Rust structs end with # (similar to classes)."""
        assert get_symbol_type("sample_rust/Calculator#") == "class"
        assert get_symbol_type("sample_rust/utils/Config#") == "class"

    def test_trait_detection(self):
        """Rust traits end with # and should be detected."""
        # Traits are also indicated by # suffix, but we'll treat them as class
        # since they define a type-like interface
        assert get_symbol_type("sample_rust/Displayable#") == "class"

    def test_enum_detection(self):
        """Rust enums end with # (similar to classes)."""
        assert get_symbol_type("sample_rust/OperationType#") == "class"

    def test_module_detection(self):
        """Rust modules end with / or :."""
        assert get_symbol_type("sample_rust/operations/") == "module"
        assert get_symbol_type("sample_rust/utils:") == "module"
        # Crate root
        assert get_symbol_type("sample_rust/") == "module"

    def test_parameter_detection(self):
        """Rust parameters use (param_name) suffix."""
        assert get_symbol_type("sample_rust/Calculator#add().(x)") == "parameter"
        assert get_symbol_type("sample_rust/helper_function().(data)") == "parameter"

    def test_field_detection(self):
        """Rust struct fields end with . but not ()."""
        assert get_symbol_type("sample_rust/Calculator#value.") == "attribute"
        assert get_symbol_type("sample_rust/Config#name.") == "attribute"

    def test_enum_variant_detection(self):
        """Rust enum variants contain # and end with #."""
        # Enum variants like OperationType::Add
        assert get_symbol_type("sample_rust/OperationType#Add#") == "attribute"

    def test_is_callable_function(self):
        """Functions are callable."""
        assert is_callable("sample_rust/helper_function().") is True

    def test_is_callable_method(self):
        """Methods are callable."""
        assert is_callable("sample_rust/Calculator#add().") is True

    def test_is_callable_attribute_not_callable(self):
        """Attributes are not callable."""
        assert is_callable("sample_rust/Calculator#value.") is False

    def test_is_callable_struct_not_callable(self):
        """Structs are not callable (constructors are separate)."""
        assert is_callable("sample_rust/Calculator#") is False

    def test_is_callable_module_not_callable(self):
        """Modules are not callable."""
        assert is_callable("sample_rust/operations/") is False


class TestRustSymbolEdgeCases:
    """Test edge cases in Rust symbol detection."""

    def test_impl_block_methods(self):
        """Methods from impl blocks should be detected."""
        # Regular impl
        assert get_symbol_type("sample_rust/Calculator#calculate_expression().") == "method"
        # Trait impl
        assert get_symbol_type("sample_rust/Calculator#[Displayable]format().") == "method"

    def test_associated_functions(self):
        """Associated functions (like new) are methods."""
        assert get_symbol_type("sample_rust/Calculator#new().") == "method"

    def test_nested_modules(self):
        """Nested modules should be detected."""
        assert get_symbol_type("sample_rust/a/b/c/") == "module"

    def test_generic_types(self):
        """Generic types should still be detected as classes."""
        # Generic struct
        assert get_symbol_type("sample_rust/Container#") == "class"

    def test_lifetime_parameters(self):
        """Symbols with lifetime annotations should be handled."""
        # The symbol descriptor should not include lifetime syntax
        assert get_symbol_type("sample_rust/RefHolder#") == "class"

    def test_unknown_symbol(self):
        """Unknown symbols should return 'unknown'."""
        assert get_symbol_type("") == "unknown"
        assert get_symbol_type("just_a_name") == "unknown"
