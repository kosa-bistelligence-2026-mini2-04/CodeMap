DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BASE_URL = "http://localhost:8000"


def get_config() -> dict:
    return {
        "timeout": DEFAULT_TIMEOUT,
        "retries": MAX_RETRIES,
        "base_url": BASE_URL,
    }
