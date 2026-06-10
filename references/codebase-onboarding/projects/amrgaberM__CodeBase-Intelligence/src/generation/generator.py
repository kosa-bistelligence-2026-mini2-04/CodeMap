"""LLM Generator using Groq API."""

from typing import Dict, List, Any, Optional, Generator
import os

from ..utils import config, logger
from .prompts import SYSTEM_PROMPT, build_prompt


# Token limits for Groq free tier
MAX_CONTEXT_TOKENS = 8000  # Leave room for response
APPROX_CHARS_PER_TOKEN = 4


class CodeGenerator:
    """Generate responses using LLM (Groq)."""
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize the generator.
        
        Args:
            model: Model name to use
            temperature: Generation temperature
            max_tokens: Max tokens in response
        """
        self.model = model or config.get("llm.model", "llama-3.3-70b-versatile")
        self.temperature = temperature or config.get("llm.temperature", 0.1)
        self.max_tokens = max_tokens or config.get("llm.max_tokens", 4096)
        
        self._client = None
        
        logger.info(f"Generator initialized with model: {self.model}")
    
    @property
    def client(self):
        """Lazy load Groq client."""
        if self._client is None:
            from groq import Groq
            
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY not found. "
                    "Set it in your .env file or environment."
                )
            
            self._client = Groq(api_key=api_key)
        return self._client
    
    def _truncate_results(self, results: List[Dict[str, Any]], max_chars: int = None) -> List[Dict[str, Any]]:
        """Truncate results to fit within token limit."""
        max_chars = max_chars or (MAX_CONTEXT_TOKENS * APPROX_CHARS_PER_TOKEN)
        
        truncated = []
        total_chars = 0
        
        for result in results:
            content = result.get("content", "")
            content_chars = len(content)
            
            # If this chunk would exceed limit, truncate or skip
            if total_chars + content_chars > max_chars:
                # If we have no results yet, truncate this one
                if not truncated:
                    remaining = max_chars - total_chars
                    truncated_content = content[:remaining] + "\n... [truncated]"
                    truncated_result = result.copy()
                    truncated_result["content"] = truncated_content
                    truncated.append(truncated_result)
                break
            
            truncated.append(result)
            total_chars += content_chars
        
        return truncated
    
    def generate(
        self,
        query: str,
        results: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response based on query and retrieved context.
        
        Args:
            query: User's question
            results: Retrieved code chunks
            system_prompt: Optional custom system prompt
            
        Returns:
            Generated response
        """
        # Truncate results to fit token limit
        truncated_results = self._truncate_results(results)
        
        if len(truncated_results) < len(results):
            logger.info(f"Truncated results from {len(results)} to {len(truncated_results)} to fit token limit")
        
        # Build prompt
        user_prompt = build_prompt(query, truncated_results)
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        return response.choices[0].message.content
    
    def generate_stream(
        self,
        query: str,
        results: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming response.
        
        Args:
            query: User's question
            results: Retrieved code chunks
            system_prompt: Optional custom system prompt
            
        Yields:
            Response tokens as they're generated
        """
        # Truncate results to fit token limit
        truncated_results = self._truncate_results(results)
        
        # Build prompt
        user_prompt = build_prompt(query, truncated_results)
        
        # Call LLM with streaming
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def explain_code(self, code: str) -> str:
        """Generate explanation for a code snippet.
        
        Args:
            code: Code to explain
            
        Returns:
            Explanation
        """
        # Truncate code if too long
        max_code_chars = MAX_CONTEXT_TOKENS * APPROX_CHARS_PER_TOKEN // 2
        if len(code) > max_code_chars:
            code = code[:max_code_chars] + "\n... [truncated]"
        
        prompt = f"""Explain what this code does in detail:

```
{code}
```

Provide:
1. A brief summary
2. Step-by-step explanation
3. Key concepts used
4. Potential issues or improvements
"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        
        return response.choices[0].message.content
