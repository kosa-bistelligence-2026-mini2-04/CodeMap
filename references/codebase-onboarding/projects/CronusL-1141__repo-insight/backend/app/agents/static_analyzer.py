from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from app.agents.base import BaseAgent
from app.models.agent_schemas import (
    FunctionRisk,
    LineRisk,
    ModuleCoverage,
    RiskLevel,
    StaticAnalyzerInput,
    StaticResult,
)

# Directories and file patterns to exclude from scanning
_SKIP_DIRS = {"__pycache__", "tests", "venv", ".venv", "node_modules"}
_SKIP_SUFFIXES = {".pyc"}

# Cyclomatic complexity to RiskLevel mapping
_CC_RISK_MAP = [
    (5, RiskLevel.LOW),
    (10, RiskLevel.MEDIUM),
    (15, RiskLevel.HIGH),
]

# Sub-budgets in seconds. These are caps on individual subprocess calls.
# pylint / radon run CONCURRENTLY via asyncio.gather, so the effective static
# analyzer wall-clock is max(pylint, radon) + coverage read time, capped by
# Planner's BUDGET_STATIC_S=85s.
#
# pylint is single-threaded per process by default; we pass --jobs=4 to fan
# out across 4 worker processes for a ~4x speedup on repos with >50 files.
_PYLINT_BUDGET = 75.0
_RADON_BUDGET = 75.0
_COVERAGE_BUDGET = 15.0
_PYLINT_JOBS = 4  # pylint --jobs parameter (multi-process parallelism)


def _cc_to_risk_level(cc: int) -> RiskLevel:
    for threshold, level in _CC_RISK_MAP:
        if cc <= threshold:
            return level
    return RiskLevel.CRITICAL


def _risk_level_max(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    return a if order.index(a) >= order.index(b) else b


def _collect_python_files(repo_path: str) -> list[str]:
    """Return relative paths of all .py files under repo_path, excluding skip dirs."""
    root = Path(repo_path)
    result: list[str] = []
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).parts
        # Skip if any path component is a skip dir, or filename matches test patterns
        if any(part in _SKIP_DIRS for part in parts):
            continue
        if path.suffix in _SKIP_SUFFIXES:
            continue
        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            continue
        result.append(str(path.relative_to(root)))
    return result


def _stage_python_files(repo_path: str, python_files: list[str]) -> str:
    """Copy the target .py files into a fresh ext4 temp dir preserving relative paths.

    Workaround for Docker Desktop Windows bind-mount per-file syscall overhead:
    pylint/radon re-open each file several times, and each open on a virtiofs-
    backed path can take 50-500ms. By staging the .py-only subset (typically
    1-5 MB) into /tmp (native container ext4), subsequent tool runs become
    100x cheaper per file-open.

    Returns the absolute staging directory path. Caller is responsible for
    cleanup via shutil.rmtree.
    """
    staged_root = tempfile.mkdtemp(prefix="repo_insight_stage_")
    src_root = Path(repo_path)
    dst_root = Path(staged_root)
    for rel in python_files:
        src = src_root / rel
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            # Best-effort: a single missing/unreadable file must not abort the whole run
            logger.warning("stage copy failed for %s: %s", rel, exc)
    return staged_root


async def _run_subprocess(args: list[str], timeout: float) -> bytes:
    """Run a subprocess without shell=True and return stdout bytes."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return stdout


async def _run_pylint(
    target_path: str,
    python_files: list[str],
    pylint_threshold: float,
) -> dict[str, float]:
    """Run pylint on the target and return {module_path: score}."""
    if not python_files:
        return {}

    args = [
        "pylint",
        "--output-format=json",
        f"--jobs={_PYLINT_JOBS}",  # fan out across N worker processes
        target_path,
    ]
    try:
        stdout = await _run_subprocess(args, _PYLINT_BUDGET)
    except asyncio.TimeoutError:
        # Large repos (>150 files) regularly exceed 20s pylint budget.
        # Degrade gracefully — radon still provides CC data.
        logger.warning(
            "pylint timed out after %ds on %s (degrading to empty scores)",
            _PYLINT_BUDGET, target_path,
        )
        return {}
    except Exception as exc:
        logger.warning(
            "pylint subprocess failed (degrading to empty scores): %s: %s",
            exc.__class__.__name__, exc,
        )
        return {}

    pylint_scores: dict[str, float] = {}
    try:
        messages = json.loads(stdout.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("pylint JSON parse failed: %s", exc)
        return {}

    # Aggregate messages per module to compute a crude score
    # pylint JSON output includes a final score in a separate format; we use
    # message counts as a proxy: score = 10.0 - (errors*2 + warnings*0.5) / file_count
    per_file_counts: dict[str, dict[str, int]] = {}
    for msg in messages:
        msg_type = msg.get("type", "")
        path = msg.get("path", "")
        if not path:
            continue
        if path not in per_file_counts:
            per_file_counts[path] = {"error": 0, "warning": 0, "convention": 0}
        if msg_type in per_file_counts[path]:
            per_file_counts[path][msg_type] += 1

    for rel_path in python_files:
        counts = per_file_counts.get(rel_path, {})
        errors = counts.get("error", 0)
        warnings = counts.get("warning", 0)
        conventions = counts.get("convention", 0)
        # Simple scoring formula: start at 10, deduct per issue
        score = max(0.0, 10.0 - errors * 2.0 - warnings * 0.5 - conventions * 0.1)
        pylint_scores[rel_path] = round(score, 2)

    return pylint_scores


async def _run_radon(
    target_path: str,
    cc_threshold: int,
) -> tuple[list[FunctionRisk], dict[str, list[LineRisk]]]:
    """Run radon cc and return high-complexity FunctionRisk list and heatmap entries."""
    args = ["radon", "cc", "-j", target_path]
    try:
        stdout = await _run_subprocess(args, _RADON_BUDGET)
    except asyncio.TimeoutError:
        logger.warning(
            "radon timed out after %ds on %s (degrading to empty cc)",
            _RADON_BUDGET, target_path,
        )
        return [], {}
    except Exception as exc:
        logger.warning(
            "radon subprocess failed (degrading to empty cc list): %s: %s",
            exc.__class__.__name__, exc,
        )
        return [], {}

    try:
        data: dict[str, list[dict[str, Any]]] = json.loads(
            stdout.decode("utf-8", errors="replace")
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("radon JSON parse failed: %s", exc)
        return [], {}

    high_complexity: list[FunctionRisk] = []
    heatmap: dict[str, list[LineRisk]] = {}

    root = Path(target_path)

    for file_abs, functions in data.items():
        try:
            rel_path = str(Path(file_abs).relative_to(root))
        except ValueError:
            rel_path = file_abs

        for func in functions:
            cc: int = func.get("complexity", 1)
            name: str = func.get("name", "unknown")
            lineno: int = func.get("lineno", 1)
            risk = _cc_to_risk_level(cc)

            if cc > cc_threshold:
                high_complexity.append(
                    FunctionRisk(
                        file=rel_path,
                        line=lineno,
                        name=name,
                        cc=cc,
                        risk_level=risk,
                        suggestion=(
                            f"函数 {name} 的圈复杂度达到 {cc}，建议拆分为更小的子函数，"
                            "提取重复逻辑、合并分支，将圈复杂度降至阈值以下以提升可读性与可测性。"
                        ),
                    )
                )

            # Add to heatmap for HIGH and CRITICAL entries
            if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                entry = LineRisk(
                    line=lineno,
                    risk_level=risk,
                    reason=f"High cyclomatic complexity CC={cc}",
                )
                heatmap.setdefault(rel_path, []).append(entry)

    return high_complexity, heatmap


def _read_coverage(
    repo_path: str,
    coverage_threshold: float,
) -> tuple[list[ModuleCoverage], dict[str, list[LineRisk]]]:
    """Read existing coverage.json and return low-coverage modules and heatmap entries."""
    coverage_path = Path(repo_path) / "coverage.json"
    if not coverage_path.exists():
        return [], {}

    try:
        with open(coverage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [], {}

    root = Path(repo_path)
    low_coverage: list[ModuleCoverage] = []
    heatmap: dict[str, list[LineRisk]] = {}

    files: dict[str, Any] = data.get("files", {})
    for file_abs, file_data in files.items():
        try:
            rel_path = str(Path(file_abs).relative_to(root))
        except ValueError:
            rel_path = file_abs

        executed = file_data.get("executed_lines", [])
        missing = file_data.get("missing_lines", [])
        total = len(executed) + len(missing)
        if total == 0:
            coverage_pct = 100.0
        else:
            coverage_pct = round(len(executed) / total * 100.0, 2)

        if coverage_pct < coverage_threshold:
            low_coverage.append(
                ModuleCoverage(
                    path=rel_path,
                    coverage_pct=coverage_pct,
                    uncovered_lines=sorted(missing),
                )
            )
            # Add uncovered lines to heatmap
            for line in missing:
                entry = LineRisk(
                    line=line,
                    risk_level=RiskLevel.MEDIUM,
                    reason="Uncovered by tests",
                )
                heatmap.setdefault(rel_path, []).append(entry)

    return low_coverage, heatmap


def _merge_heatmaps(
    radon_heatmap: dict[str, list[LineRisk]],
    coverage_heatmap: dict[str, list[LineRisk]],
) -> dict[str, list[LineRisk]]:
    """Merge two heatmaps, taking max risk_level per line."""
    merged: dict[str, dict[int, LineRisk]] = {}

    for file_path, entries in radon_heatmap.items():
        for entry in entries:
            merged.setdefault(file_path, {})[entry.line] = entry

    for file_path, entries in coverage_heatmap.items():
        for entry in entries:
            existing = merged.get(file_path, {}).get(entry.line)
            if existing is None:
                merged.setdefault(file_path, {})[entry.line] = entry
            else:
                # Take the higher risk level, keep the radon reason if same level
                max_level = _risk_level_max(existing.risk_level, entry.risk_level)
                if max_level != existing.risk_level:
                    merged[file_path][entry.line] = LineRisk(
                        line=entry.line,
                        risk_level=max_level,
                        reason=entry.reason,
                    )
                else:
                    merged[file_path][entry.line] = LineRisk(
                        line=existing.line,
                        risk_level=max_level,
                        reason=existing.reason,
                    )

    return {
        file_path: sorted(entries.values(), key=lambda e: e.line)
        for file_path, entries in merged.items()
    }


_SUGGESTION_PROMPT = """你是 RepoInsight 代码重构专家 Agent。仓库静态分析发现以下高圈复杂度函数，请结合每个函数的源码片段，为每个函数产出一条针对性的中文重构建议。

## 输入
{snippets}

## 输出要求
- 必须为合法 JSON，禁止 markdown 代码块包裹
- 每条建议针对该函数的**具体代码特征**，不要套用通用话术
- 指出"具体问题"（例如嵌套过深、分支爆炸、重复逻辑），并给出"可执行步骤"
- 每条建议 60-120 字之间
- 禁止编造源码中不存在的内容

## 输出格式
{{
  "suggestions": [
    {{"function": "<函数名>", "file": "<文件路径>", "suggestion": "<中文重构建议>"}},
    ...
  ]
}}
只输出 JSON，不要任何前后缀说明。
"""


def _read_function_snippet(repo_path: str, rel_path: str, line: int, ctx: int = 12) -> str:
    """Read ±ctx lines around `line` from `repo_path/rel_path` as a code snippet."""
    try:
        abs_path = Path(repo_path) / rel_path
        lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    start = max(0, line - 1 - ctx)
    end = min(len(lines), line - 1 + ctx + 1)
    numbered = "\n".join(
        f"{i + 1:>4}: {lines[i]}" for i in range(start, end)
    )
    return numbered


class StaticAnalyzer(BaseAgent):
    """Runs pylint + radon + coverage to produce complexity and coverage metrics.

    Enhanced with an LLM "refactor advisor" pass: after deterministic tool output
    finds the Top-N high-complexity functions, their source snippets are sent to
    an LLM to generate targeted Chinese refactoring suggestions. The LLM output
    overwrites each FunctionRisk.suggestion field. If the LLM call fails, the
    template fallback from `_run_radon` is preserved — no regression.
    """

    name = "static_analyzer"

    def __init__(
        self,
        llm_provider=None,
        cache=None,
        top_n_for_llm: int = 3,
    ) -> None:
        self.llm_provider = llm_provider
        self.cache = cache
        self.top_n_for_llm = top_n_for_llm

    async def _generate_llm_suggestions(
        self,
        repo_path: str,
        high_complexity: list[FunctionRisk],
    ) -> None:
        """LLM pass: rewrite `suggestion` fields for the Top-N riskiest functions.

        Best-effort — mutates `high_complexity` in place. Any error leaves the
        template fallback untouched.
        """
        if self.llm_provider is None or not high_complexity:
            return

        top = sorted(high_complexity, key=lambda f: f.cc, reverse=True)[: self.top_n_for_llm]

        # Build snippets block for the prompt
        snippet_blocks: list[str] = []
        for idx, func in enumerate(top, start=1):
            snippet = _read_function_snippet(repo_path, func.file, func.line, ctx=15)
            if not snippet:
                continue
            snippet_blocks.append(
                f"### 函数 {idx}\n"
                f"- file: `{func.file}`\n"
                f"- name: `{func.name}`\n"
                f"- 圈复杂度 CC: {func.cc}\n"
                f"- 起始行: {func.line}\n"
                f"- 源码片段:\n```python\n{snippet}\n```"
            )

        if not snippet_blocks:
            return

        prompt = _SUGGESTION_PROMPT.format(snippets="\n\n".join(snippet_blocks))

        # Cache key derived from prompt hash so identical inputs reuse results
        cache_key_str = None
        if self.cache is not None:
            import hashlib
            cache_key_str = "static_llm_suggest::" + hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest()[:32]
            try:
                cached = await self.cache.get(cache_key_str)
                if cached:
                    self._apply_llm_json(cached, top)
                    return
            except Exception:
                pass

        try:
            raw = await asyncio.wait_for(
                self.llm_provider.complete(
                    prompt=prompt,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                ),
                timeout=20.0,
            )
        except Exception:
            return

        if not raw:
            return

        if cache_key_str is not None and self.cache is not None:
            try:
                await self.cache.set(cache_key_str, raw)
            except Exception:
                pass

        self._apply_llm_json(raw, top)

    @staticmethod
    def _apply_llm_json(raw: str, top: list[FunctionRisk]) -> None:
        try:
            payload = json.loads(raw)
            items = payload.get("suggestions", [])
            if not isinstance(items, list):
                return
        except (json.JSONDecodeError, TypeError, AttributeError):
            return

        # Match by (file, name); first-match wins, safe when LLM returns fewer items
        by_key = {(f.file, f.name): f for f in top}
        for item in items:
            if not isinstance(item, dict):
                continue
            file_v = str(item.get("file", "")).strip()
            name_v = str(item.get("function", "")).strip()
            suggestion = str(item.get("suggestion", "")).strip()
            if not suggestion:
                continue
            target = by_key.get((file_v, name_v))
            if target is None:
                # Fallback: match by name only
                for (f, n), cand in by_key.items():
                    if n == name_v:
                        target = cand
                        break
            if target is not None:
                target.suggestion = suggestion[:500]

    async def run(self, input_data: StaticAnalyzerInput) -> StaticResult:
        t_start = time.monotonic()

        repo_path = input_data.repo_path
        # rglob on large bind-mounted repos (e.g. 7000+ dirs via Docker Desktop)
        # can block the event loop for tens of seconds — offload to a thread so
        # WebSocket handshakes and other agents stay responsive.
        python_files = await asyncio.to_thread(_collect_python_files, repo_path)
        total_files_scanned = len(python_files)

        # Stage the .py subset to a native ext4 temp dir so pylint/radon avoid
        # the Windows Docker Desktop bind-mount per-file syscall tax. On Linux
        # native bind mounts this is a near-zero-cost copy of a few MB; on
        # Windows it turns 85s+ degraded runs into ~50s clean completions.
        staged_path: str | None = None
        try:
            if python_files:
                staged_path = await asyncio.to_thread(
                    _stage_python_files, repo_path, python_files
                )
            analysis_path = staged_path or repo_path

            # Run pylint and radon concurrently, then read coverage (file read, no subprocess)
            pylint_task = asyncio.create_task(
                _run_pylint(analysis_path, python_files, input_data.pylint_threshold)
            )
            radon_task = asyncio.create_task(
                _run_radon(analysis_path, input_data.cc_threshold)
            )

            pylint_scores, (high_complexity, radon_heatmap) = await asyncio.gather(
                pylint_task, radon_task
            )

            # Coverage always reads from the original repo (coverage.json sits
            # alongside the source tree and references source-tree paths).
            low_coverage, coverage_heatmap = _read_coverage(
                repo_path, input_data.coverage_threshold
            )

            # LLM refactor advisor pass (best-effort, won't block if provider is None or fails).
            # Snippet reader uses `repo_path` so it finds the original source files.
            await self._generate_llm_suggestions(repo_path, high_complexity)
        finally:
            if staged_path:
                try:
                    await asyncio.to_thread(shutil.rmtree, staged_path, True)
                except Exception as exc:
                    logger.warning("stage cleanup failed for %s: %s", staged_path, exc)

        file_heatmap = _merge_heatmaps(radon_heatmap, coverage_heatmap)

        duration_ms = int((time.monotonic() - t_start) * 1000)

        return StaticResult(
            job_id=input_data.job_id,
            high_complexity_functions=high_complexity,
            low_coverage_modules=low_coverage,
            file_heatmap=file_heatmap,
            pylint_scores=pylint_scores,
            total_files_scanned=total_files_scanned,
            duration_ms=duration_ms,
        )
