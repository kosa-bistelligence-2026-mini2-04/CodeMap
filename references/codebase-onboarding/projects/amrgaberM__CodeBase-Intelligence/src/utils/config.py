"""Configuration management for CodeBase RAG."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager that loads from YAML and environment variables."""
    
    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> "Config":
        """Singleton pattern to ensure single config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent.parent.parent / "configs" / "config.yaml"
        
        if config_path.exists():
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f)
        else:
            print(f"Warning: Config file not found at {config_path}")
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Example:
            config.get("llm.model") -> "llama-3.3-70b-versatile"
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def groq_api_key(self) -> str:
        """Get Groq API key from environment."""
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        return key
    
    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self._config.get("llm", {})
    
    @property
    def embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration."""
        return self._config.get("embeddings", {})
    
    @property
    def chunking_config(self) -> Dict[str, Any]:
        """Get chunking configuration."""
        return self._config.get("chunking", {})
    
    @property
    def retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration."""
        return self._config.get("retrieval", {})
    
    @property
    def vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration."""
        return self._config.get("vector_store", {})
    
    @property
    def supported_extensions(self) -> list:
        """Get list of supported file extensions."""
        return self._config.get("supported_extensions", [".py", ".js", ".md"])
    
    @property
    def ignore_patterns(self) -> list:
        """Get list of patterns to ignore."""
        return self._config.get("ignore_patterns", ["node_modules", "__pycache__", ".git"])


# Global config instance
config = Config()
