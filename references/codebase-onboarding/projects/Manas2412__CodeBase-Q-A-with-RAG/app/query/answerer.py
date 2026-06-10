# app/query/answerer.py
import httpx
import json
from typing import AsyncIterator
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL")

SYSTEM_PROMPT = (
    "You are a senior engineer answering questions about a codebase. "
    "Answer using ONLY the provided code context. "
    "Always cite the file path and function name when referencing code. "
    "If the answer is not in the context, say so clearly — do not guess."
)

async def stream_answer(query: str, chunks: list[dict]) -> AsyncIterator[str]:
    """Stream token-by-token answer from local Ollama."""

    context = "\n\n---\n\n".join(
        f"# {c['context_prefix']} (line {c['start_line']})\n"
        f"```python\n{c['content']}\n```"
        for c in chunks
    )

    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Code context:\n{context}\n\n"
        f"Question: {query}"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model":  OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": True,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1500,
                },
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if token := chunk.get("response"):
                    yield token
                if chunk.get("done"):
                    break