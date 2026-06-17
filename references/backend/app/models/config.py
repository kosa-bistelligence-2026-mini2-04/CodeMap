import os

class Settings:
    """Mock backend configuration settings."""
    PORT: int = int(os.getenv("PORT", 8001))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    PROVIDER: str = os.getenv("PROVIDER", "openai")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o")

settings = Settings()
