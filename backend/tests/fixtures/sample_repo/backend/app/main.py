from fastapi import FastAPI

from backend.app.service import build_message

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"message": build_message("ready")}
