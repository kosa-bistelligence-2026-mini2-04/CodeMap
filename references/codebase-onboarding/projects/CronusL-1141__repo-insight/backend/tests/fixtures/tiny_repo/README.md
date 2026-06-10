# tiny_repo

A minimal fixture repository used for StaticAnalyzer unit tests.

## Files

- `simple.py` — Low CC (basic arithmetic helpers)
- `utils.py` — Low CC (clamp, parity)
- `config.py` — Low CC (constants)
- `parser.py` — Medium CC (token parsing)
- `router.py` — Medium CC (HTTP routing)
- `analyzer.py` — High CC (AST traversal)
- `complex_logic.py` — High CC (nested processing pipeline)
- `god_object.py` — CRITICAL CC (monolithic handler)
- `tests/test_simple.py` — Full-coverage test file
