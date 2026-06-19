from backend.app.config import SERVICE_PREFIX


def build_message(value: str) -> str:
    return f"{SERVICE_PREFIX}:{value}"
