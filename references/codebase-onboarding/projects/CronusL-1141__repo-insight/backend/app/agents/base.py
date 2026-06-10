from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all analysis agents."""

    name: str = "base"

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Execute the agent's analysis and return a typed result."""
        ...
