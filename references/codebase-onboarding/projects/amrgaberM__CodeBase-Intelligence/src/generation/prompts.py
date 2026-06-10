"""Code-aware prompts for the RAG system."""

SYSTEM_PROMPT = """You are an expert code assistant that helps developers understand codebases.

You have access to relevant code snippets from the repository. When answering:

1. **Focus on CODE**: Prioritize actual source code (functions, classes) over documentation or config files
2. **Be precise**: Reference specific files, functions, and line numbers
3. **Show code**: Include relevant code snippets in your answers
4. **Explain context**: Describe how components relate to each other
5. **Be honest**: If you don't have enough context, say so

For "what is this project" or "core idea" questions:
- Look for the main module, README, or __init__.py
- Identify the primary classes and functions
- Explain the project's PURPOSE, not its management/docs

Format your responses clearly with:
- Code blocks using triple backticks with language identifier
- File paths in `backticks`
- Function/class names in **bold**

Remember: The user is a developer who wants to understand and work with this codebase."""


QUERY_PROMPT_TEMPLATE = """Based on the following code context from the repository, answer the user's question.

## Retrieved Code Context

{context}

## User Question

{query}

## Instructions

1. Answer based ONLY on the provided code context
2. **Prioritize actual source code** over documentation, management files, or configs
3. If the question asks about "core idea" or "what does this do", focus on:
   - Main classes and their purpose
   - Key functions and what they do
   - How the pieces fit together
4. If the context doesn't contain enough information, say so
5. Reference specific files and line numbers when relevant
6. Include relevant code snippets in your answer

## Answer
"""


CONTEXT_TEMPLATE = """### File: `{file_path}`
**{chunk_type}**: {name}
Lines {start_line}-{end_line}

```{language}
{content}
```
"""


# File priority for different query types
HIGH_PRIORITY_FILES = [
    "main.py",
    "__init__.py", 
    "app.py",
    "core.py",
    "cli.py",
    "api.py",
    "README.md",
]

LOW_PRIORITY_PATTERNS = [
    "docs/management",
    "docs/release",
    ".pre-commit",
    "test_",
    "conftest",
    "setup.py",
    "setup.cfg",
]


def is_high_priority_file(file_path: str) -> bool:
    """Check if file is high priority for overview questions."""
    file_name = file_path.split("/")[-1]
    return any(hp in file_name for hp in HIGH_PRIORITY_FILES)


def is_low_priority_file(file_path: str) -> bool:
    """Check if file should be deprioritized."""
    return any(lp in file_path.lower() for lp in LOW_PRIORITY_PATTERNS)


def is_overview_question(query: str) -> bool:
    """Detect if query is asking for project overview."""
    overview_keywords = [
        "what is", "what does", "core idea", "purpose", "overview",
        "main feature", "about this", "explain this project",
        "how does this work", "what's this repo"
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in overview_keywords)


def format_context(results: list) -> str:
    """Format retrieved results into context for the LLM.
    
    Args:
        results: List of retrieval results
        
    Returns:
        Formatted context string
    """
    context_parts = []
    
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        
        # Extract content (remove the header we added for embedding)
        content = result["content"]
        if content.startswith("# File:"):
            # Remove our embedding header
            lines = content.split("\n")
            # Find where actual code starts (after empty line)
            for j, line in enumerate(lines):
                if line == "" and j > 0:
                    content = "\n".join(lines[j+1:])
                    break
        
        context_part = CONTEXT_TEMPLATE.format(
            file_path=metadata.get("file_path", "unknown"),
            chunk_type=metadata.get("chunk_type", "code").title(),
            name=metadata.get("name", "unnamed"),
            start_line=metadata.get("start_line", "?"),
            end_line=metadata.get("end_line", "?"),
            language=metadata.get("language", ""),
            content=content.strip(),
        )
        
        context_parts.append(f"[{i}] {context_part}")
    
    return "\n\n---\n\n".join(context_parts)


def build_prompt(query: str, results: list) -> str:
    """Build the full prompt for the LLM.
    
    Args:
        query: User's question
        results: Retrieved code chunks
        
    Returns:
        Complete prompt string
    """
    context = format_context(results)
    
    return QUERY_PROMPT_TEMPLATE.format(
        context=context,
        query=query,
    )


# Specialized prompts for different query types

EXPLAIN_FUNCTION_PROMPT = """Explain what the following function does:

{code}

Provide:
1. A brief summary (1-2 sentences)
2. Parameters and their purposes
3. Return value
4. Key logic/algorithm
5. Any dependencies or side effects
"""

FIND_USAGE_PROMPT = """Find all usages of `{target}` in the codebase.

Context:
{context}

List:
1. Where it's defined
2. Where it's imported
3. Where it's called/used
4. Any relevant patterns
"""

DEBUG_PROMPT = """Help debug an issue related to:

{query}

Relevant code:
{context}

Analyze:
1. Potential causes of the issue
2. Relevant code paths
3. Suggested fixes or investigations
"""
