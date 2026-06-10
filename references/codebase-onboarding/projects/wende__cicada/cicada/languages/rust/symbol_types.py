"""Rust SCIP symbol type detection.

Rust symbol descriptor patterns (from rust-analyzer SCIP output):
- sample_rust/Calculator# -> struct/class (ends with #)
- sample_rust/Calculator#add(). -> method (contains # before ().)
- sample_rust/helper_function(). -> function (no #, ends with ().)
- sample_rust/operations/ -> module (ends with /)
- sample_rust/operations: -> module (ends with :)
- sample_rust/Calculator#add().(x) -> parameter (ends with .(name))
- sample_rust/Calculator#value. -> field/attribute (ends with . but not ().)
- sample_rust/OperationType#Add# -> enum variant (contains # and ends with #)
- sample_rust/Displayable# -> trait (ends with #, same as struct)

Note: Rust uses (). suffix for callables (functions and methods).
Traits, structs, and enums all use # suffix and are treated as 'class'.
"""

import re
from typing import Literal

SymbolType = Literal["class", "method", "function", "module", "parameter", "attribute", "unknown"]


def get_symbol_type(descriptor: str) -> SymbolType:
    """
    Determine symbol type for Rust SCIP symbols.

    Args:
        descriptor: The descriptor portion of the SCIP symbol (parts after scheme/manager/package)

    Returns:
        Symbol type: 'class', 'method', 'function', 'module', 'parameter',
                    'attribute', or 'unknown'
    """
    if not descriptor:
        return "unknown"

    # Parameter: ends with .(param_name)
    if re.match(r".*\.\([^)]+\)$", descriptor):
        return "parameter"

    # Module/namespace: ends with / or :
    if descriptor.endswith(("/", ":")):
        return "module"

    # Enum variant: contains # and ends with # (like OperationType#Add#)
    # But NOT just a single # at the end (that's a struct/enum/trait definition)
    if descriptor.count("#") >= 2 and descriptor.endswith("#"):
        return "attribute"

    # Method: contains # and ends with ().
    if "#" in descriptor and descriptor.endswith("()."):
        return "method"

    # Function: no # but ends with ().
    if "#" not in descriptor and descriptor.endswith("()."):
        return "function"

    # Struct/Enum/Trait: ends with # (no method following)
    if descriptor.endswith("#"):
        return "class"

    # Field/Attribute: ends with . (but not ().)
    if descriptor.endswith(".") and not descriptor.endswith("()."):
        return "attribute"

    return "unknown"


def is_callable(descriptor: str) -> bool:
    """
    Check if a Rust symbol descriptor represents a callable.

    Args:
        descriptor: The descriptor portion of the SCIP symbol

    Returns:
        True if the symbol is a function or method
    """
    symbol_type = get_symbol_type(descriptor)
    return symbol_type in ("function", "method")
