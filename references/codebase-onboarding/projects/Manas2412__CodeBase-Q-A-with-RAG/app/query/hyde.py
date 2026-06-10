import httpx 

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "codellama:7b"

async def hyde_expand(query:str) -> str:
    """Generate a hypothetical code chunk that would answer the query.
    Embed this instead of the raw question — code embeddings are
    trained on code-to-code similarity, not NL-to-code."""

    prompt = (
        f"Write a short Python function or class that would be "
        f"the implementation for: '{query}'\n"
        f"Return ONLY the code, no explanation."
    )
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 300,
                    },
                },
            )
            response.raise_for_status()
            return response.json()["response"].strip()
    except Exception as e:
        print(f"HyDE expansion failed: {e}")
        return query