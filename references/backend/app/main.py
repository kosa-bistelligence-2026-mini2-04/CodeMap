import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes, health
from app.api.progress_bus import progress_bus

app = FastAPI(title="CodeMap AI Backend Service", version="0.1.0")

# Enable CORS for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount endpoints
app.include_router(health.router, tags=["Health Check"])
app.include_router(routes.router, prefix="/api", tags=["CodeMap API"])


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket handler routing progress events directly to the client."""
    await websocket.accept()
    try:
        async for event in progress_bus.subscribe(job_id):
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        progress_bus.cleanup(job_id)
