import sys
import importlib


def test_behavior_inferer_does_not_pull_guardrail():
    for mod in list(sys.modules):
        if mod.startswith("app.guardrail"):
            del sys.modules[mod]
    importlib.import_module("app.agents.behavior_inferer")
    leaked = [m for m in sys.modules if m.startswith("app.guardrail")]
    assert not leaked, f"behavior_inferer leaked guardrail imports via reflection: {leaked}"
