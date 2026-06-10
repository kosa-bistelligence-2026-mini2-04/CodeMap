import httpx
import time
import asyncio
import json

BASE_URL = "http://127.0.0.1:8000"
REPO_URL = "https://github.com/Manas2412/CodeBase-Q-A-with-RAG"

async def test():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Add repo
        print(f"Adding repo: {REPO_URL}")
        resp = await client.post(f"{BASE_URL}/repos", json={"github_url": REPO_URL})
        print(f"Status Add: {resp.status_code}")
        data = resp.json()
        print(f"Data Add: {data}")
        repo_id = data["repo_id"]
        
        # 2. Wait for completion
        print("Waiting for indexing to complete...")
        while True:
            resp = await client.get(f"{BASE_URL}/repos/{repo_id}/status")
            status_data = resp.json()
            status = status_data["status"]
            print(f"Current Status: {status}")
            if status == "ready":
                break
            if status == "error":
                print("Error during indexing!")
                return
            await asyncio.sleep(5)
            
        # 3. Query
        print("Querying repo...")
        question = "How does the ingestion cloner work?"
        async with client.stream("POST", f"{BASE_URL}/query", json={"repo_id": repo_id, "question": question}) as response:
            print(f"Query Resp: {response.status_code}")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    content = line[6:]
                    print(content, end="", flush=True)
        print("\nTest complete.")

if __name__ == "__main__":
    asyncio.run(test())
