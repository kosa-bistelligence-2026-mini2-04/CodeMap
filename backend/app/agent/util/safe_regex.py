"""Safe Regex module for ReDoS protection."""

import functools
import re
import regex

class RegexTimeoutError(Exception):
    """Raised when regex execution exceeds the time limit."""
    pass

_MAX_PATTERN_LENGTH = 128
_NESTED_QUANTIFIER = regex.compile(r"\([^)]*[+*][^)]*\)\s*[+*?{]")

@functools.lru_cache(maxsize=128)
def compile_safe_regex(pattern: str, flags: int = 0) -> regex.Pattern:
    """Compile regex after length and nesting checks."""
    if not pattern or not pattern.strip():
        raise ValueError("Empty pattern")
    if len(pattern) > _MAX_PATTERN_LENGTH:
        raise ValueError(f"Pattern exceeds max length of {_MAX_PATTERN_LENGTH}")
    if _NESTED_QUANTIFIER.search(pattern):
        raise ValueError("Pattern contains nested quantifiers (ReDoS risk)")
    return regex.compile(pattern, flags)
