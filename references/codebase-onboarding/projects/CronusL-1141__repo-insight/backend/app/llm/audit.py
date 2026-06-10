from __future__ import annotations

import time
from pathlib import Path

_DEFAULT_DB_PATH = Path("data/llm_audit.db")

_LLM_AUDIT_SCHEMA = """
    CREATE TABLE IF NOT EXISTS llm_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        agent_name TEXT,
        model TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        cost_usd REAL,
        cache_hit INTEGER DEFAULT 0,
        cache_key TEXT
    )
"""


async def _ensure_audit_table(db_path: str) -> None:
    """Create llm_audit_log table if it doesn't exist."""
    import aiosqlite
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_LLM_AUDIT_SCHEMA)
        await db.commit()

# Per 1K-token prices in USD. Sources: OpenAI / DeepSeek / Qwen / Zhipu / Moonshot
# official pricing pages (2026-04).
_DEFAULT_PRICES = {
    # OpenAI
    "gpt-5.4":      {"input": 0.00250, "output": 0.01500},
    "gpt-5.4-mini": {"input": 0.00075, "output": 0.00450},
    "gpt-5.4-nano": {"input": 0.00020, "output": 0.00125},
    # DeepSeek V3.2
    "deepseek-chat":     {"input": 0.00028, "output": 0.00042},
    "deepseek-reasoner": {"input": 0.00028, "output": 0.00042},
    # Qwen
    "qwen3-max":         {"input": 0.00250, "output": 0.01000},
    "qwen3.5-plus":      {"input": 0.00080, "output": 0.00200},
    "qwen3.5-flash":     {"input": 0.00030, "output": 0.00060},
    "qwen-long-latest":  {"input": 0.00050, "output": 0.00200},
    # Zhipu GLM
    "glm-5":    {"input": 0.00072, "output": 0.00060},
    "glm-4.6":  {"input": 0.00039, "output": 0.00174},
    "glm-4.5":  {"input": 0.00060, "output": 0.00220},
    # Moonshot
    "kimi-k2.5":          {"input": 0.00060, "output": 0.00300},
    "kimi-k2":            {"input": 0.00055, "output": 0.00220},
    "moonshot-v1-128k":   {"input": 0.00060, "output": 0.00240},
}


def estimate_cost_usd(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    price = _DEFAULT_PRICES.get(model) or _DEFAULT_PRICES["gpt-5.4"]
    return (prompt_tokens / 1000.0) * price["input"] + (
        completion_tokens / 1000.0
    ) * price["output"]


class AuditLogger:
    _SCHEMA = (
        "CREATE TABLE IF NOT EXISTS audit_log ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  created_at REAL NOT NULL,"
        "  key TEXT,"
        "  agent_name TEXT,"
        "  model TEXT,"
        "  prompt_tokens INTEGER NOT NULL,"
        "  completion_tokens INTEGER NOT NULL,"
        "  cost_usd REAL NOT NULL,"
        "  cache_hit INTEGER NOT NULL,"
        "  error TEXT"
        ")"
    )

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(self._SCHEMA)
            await db.commit()
        self._initialized = True

    async def record(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit: bool,
        key: str | None = None,
        agent_name: str | None = None,
        error: str | None = None,
        cost_usd: float | None = None,
    ) -> None:
        await self._ensure_schema()
        import aiosqlite

        if cost_usd is None:
            cost_usd = (
                0.0
                if cache_hit or error == "budget_exhausted"
                else estimate_cost_usd(model, prompt_tokens, completion_tokens)
            )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO audit_log("
                "  created_at, key, agent_name, model,"
                "  prompt_tokens, completion_tokens, cost_usd, cache_hit, error"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    key,
                    agent_name,
                    model,
                    int(prompt_tokens),
                    int(completion_tokens),
                    float(cost_usd),
                    1 if cache_hit else 0,
                    error,
                ),
            )
            await db.commit()
