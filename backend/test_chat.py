import asyncio
import httpx

async def test_chat():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Login
        login_data = {"email": "test1@codemap.com", "password": "test1234!"}
        print("Logging in...")
        resp = await client.post("/api/auth/login", json=login_data)
        if resp.status_code != 200:
            print("Login failed:", resp.text)
            return
        
        login_resp = resp.json()
        print("Login response:", login_resp)
        if "data" in login_resp and "accessToken" in login_resp["data"]:
            token = login_resp["data"]["accessToken"]
        else:
            token = login_resp.get("accessToken")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Repositories
        print("Fetching repositories...")
        resp = await client.get("/api/list/analysis", headers=headers)
        if resp.status_code != 200:
            print("Failed to get repos:", resp.text)
            return
            
        repos_json = resp.json()
        print("Repos response:", repos_json)
        repos = repos_json.get("data", {}).get("jobs", []) if isinstance(repos_json.get("data"), dict) else repos_json.get("data", [])
        if not repos:
            print("No repos found.")
            return
            
        repo_id = repos[0]["jobId"]
        print(f"Using repo_id: {repo_id}")
        
        # Create dummy directory to bypass clone check
        import os
        clone_dir = f"/tmp/codemap/jobs/{repo_id}/repo"
        os.makedirs(clone_dir, exist_ok=True)
        # Also write a dummy file
        with open(os.path.join(clone_dir, "dummy.txt"), "w") as f:
            f.write("Hello World")
            
        # 3. Create Chat Run
        print("Creating chat run...")
        chat_req = {"question": "Hello, how does this repo work?", "mode": "standard"}
        resp = await client.post(f"/api/chat/{repo_id}/runs", json=chat_req, headers=headers)
        if resp.status_code != 202:
            print("Failed to create run:", resp.text)
            return
            
        run_id = resp.json().get("data", {}).get("runId")
        print(f"Run created: {run_id}")
        
        # 4. Stream Chat Run
        print("Streaming chat run...")
        async with client.stream("GET", f"/api/chat/{repo_id}/runs/{run_id}/stream", headers=headers) as stream_resp:
            if stream_resp.status_code != 200:
                print("Failed to stream:", stream_resp.status_code)
                return
                
            async for line in stream_resp.aiter_lines():
                if line:
                    print(line)

if __name__ == "__main__":
    asyncio.run(test_chat())
