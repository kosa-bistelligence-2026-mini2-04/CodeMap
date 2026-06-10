"""Tests for P0-1: OpenAI Automatic Prompt Caching prefix stability.

Verifies that _build_prompt keeps the static system/instructions prefix
identical across different dynamic inputs so OpenAI's automatic KV-cache
can reuse the prefix tokens.
"""
from __future__ import annotations

from app.agents.behavior_inferer import BehaviorInferer, _STATIC_PREFIX


def _make_inferer() -> BehaviorInferer:
    return BehaviorInferer(llm_provider=None, cache=None)


class TestStaticPrefixAtStart:
    def test_static_prefix_at_start(self):
        """The static system prefix must appear at the very beginning of every prompt."""
        inferer = _make_inferer()
        prompt = inferer._build_prompt(
            readme="Some README content about a web framework",
            issue_templates="Bug report template here",
            pr_titles=["fix: edge case", "feat: new endpoint"],
        )
        assert prompt.startswith(_STATIC_PREFIX), (
            "Static prefix must be at the start of the prompt for OpenAI prompt caching"
        )

    def test_static_prefix_identical_for_different_inputs(self):
        """The prefix portion must be byte-for-byte identical regardless of dynamic content."""
        inferer = _make_inferer()

        prompt_a = inferer._build_prompt(
            readme="README A: This is a data pipeline library.",
            issue_templates="Template A: Steps to reproduce...",
            pr_titles=["fix: null pointer", "feat: batch mode"],
        )
        prompt_b = inferer._build_prompt(
            readme="README B: A machine learning framework for NLP.",
            issue_templates="Template B: Expected vs actual behavior...",
            pr_titles=["chore: bump deps"],
        )

        prefix_len = len(_STATIC_PREFIX)
        assert prompt_a[:prefix_len] == prompt_b[:prefix_len], (
            "Static prefix diverged between two different inputs — caching will not trigger"
        )

    def test_empty_inputs_still_have_static_prefix(self):
        """Even with empty repo data the static prefix must remain intact."""
        inferer = _make_inferer()
        prompt = inferer._build_prompt(readme="", issue_templates="", pr_titles=[])
        assert prompt.startswith(_STATIC_PREFIX)


class TestDynamicPartAtEnd:
    def test_readme_appears_in_second_half(self):
        """README content must appear in the latter half of the prompt (after static prefix)."""
        inferer = _make_inferer()
        readme = "UNIQUE_README_MARKER_XYZ_12345"
        prompt = inferer._build_prompt(
            readme=readme,
            issue_templates="",
            pr_titles=[],
        )
        mid = len(prompt) // 2
        readme_pos = prompt.find(readme)
        assert readme_pos != -1, "README content not found in prompt at all"
        assert readme_pos >= mid, (
            f"README found at position {readme_pos} but prompt mid is {mid}; "
            "dynamic content must be in the second half"
        )

    def test_pr_titles_appear_after_static_prefix(self):
        """PR titles must appear after the static prefix boundary."""
        inferer = _make_inferer()
        pr_title = "UNIQUE_PR_TITLE_MARKER_ABC"
        prompt = inferer._build_prompt(
            readme="",
            issue_templates="",
            pr_titles=[pr_title],
        )
        prefix_end = len(_STATIC_PREFIX)
        title_pos = prompt.find(pr_title)
        assert title_pos != -1, "PR title not found in prompt"
        assert title_pos >= prefix_end, (
            "PR title appeared inside the static prefix region — this would break caching"
        )

    def test_issue_templates_appear_after_static_prefix(self):
        """ISSUE template content must appear after the static prefix boundary."""
        inferer = _make_inferer()
        issue_content = "UNIQUE_ISSUE_TEMPLATE_MARKER_DEF"
        prompt = inferer._build_prompt(
            readme="",
            issue_templates=issue_content,
            pr_titles=[],
        )
        prefix_end = len(_STATIC_PREFIX)
        issue_pos = prompt.find(issue_content)
        assert issue_pos != -1, "Issue template content not found in prompt"
        assert issue_pos >= prefix_end


class TestPrefixTokenCountThreshold:
    def test_prefix_character_count_above_4096(self):
        """Static prefix must exceed 4096 characters (rough proxy for >1024 tokens at ~4 chars/token).

        OpenAI Automatic Prompt Caching requires >1024 tokens of identical prefix.
        At ~4 chars per token, 4096 chars >= 1024 tokens.
        """
        prefix_chars = len(_STATIC_PREFIX)
        assert prefix_chars >= 4096, (
            f"Static prefix is only {prefix_chars} chars (~{prefix_chars // 4} tokens). "
            "OpenAI requires >=1024 tokens for automatic caching to trigger. "
            "Add more few-shot examples to the static prefix."
        )

    def test_prefix_stable_hash(self):
        """Same prefix content must hash identically (sanity check for string stability)."""
        import hashlib
        h1 = hashlib.md5(_STATIC_PREFIX.encode()).hexdigest()
        h2 = hashlib.md5(_STATIC_PREFIX.encode()).hexdigest()
        assert h1 == h2
