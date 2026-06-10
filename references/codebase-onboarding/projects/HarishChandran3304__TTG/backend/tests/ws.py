import asyncio
import websockets
import sys
from nanoid import generate


async def test_websocket(owner: str, repo: str, client_id: str) -> None:
    uri = f"ws://localhost:8000/chat/{owner}/{repo}/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Client {client_id} connected to chat for {owner}/{repo}")
            print("Processing repository...")

            # Wait for repo_processed message
            response = await websocket.recv()
            if response == "repo_processed":
                print("Repository processed successfully!")
            else:
                print("Unexpected response:", response)
                return

            # Then send queries
            while True:
                try:
                    query = input(f"Client {client_id} - Enter query (or 'quit'): ")
                    if query == "quit":
                        break
                    await websocket.send(query)
                    response = await websocket.recv()
                    print(f"Client {client_id} - Response: {response}")  # type: ignore
                except websockets.exceptions.ConnectionClosed:
                    print(f"Client {client_id} - Connection closed by server")
                    break
                except Exception as e:
                    print(f"Client {client_id} - Error: {e}")
                    break

    except websockets.exceptions.ConnectionClosed:
        print(f"Client {client_id} - Connection closed by server")
    except Exception as e:
        print(f"Client {client_id} - Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ws.py <owner> <repo>")
        print("Example: python ws.py EnhancedJax Bagels")
        sys.exit(1)

    owner = str(sys.argv[1])
    repo = str(sys.argv[2])
    client_id = generate(size=10)
    asyncio.run(test_websocket(owner, repo, client_id))
