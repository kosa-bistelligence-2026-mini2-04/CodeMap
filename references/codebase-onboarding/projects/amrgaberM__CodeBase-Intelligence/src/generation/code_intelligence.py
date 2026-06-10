from typing import Dict, List, Any, Optional
from ..utils import logger


class CodeIntelligence:
    """Smart code analysis and understanding."""
    
    def __init__(self, retriever, generator):
        self.retriever = retriever
        self.generator = generator
    
    def explain_function(self, function_name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed explanation of a function."""
        
        # Search for the function
        query = f"function {function_name}"
        if file_path:
            query += f" in {file_path}"
        
        results = self.retriever.search(query, top_k=5)
        
        # Find the exact function
        target_chunk = None
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("name") == function_name:
                target_chunk = r
                break
        
        if not target_chunk:
            # Take best match
            target_chunk = results[0] if results else None
        
        if not target_chunk:
            return {"error": f"Function '{function_name}' not found"}
        
        # Generate explanation
        prompt = f"""Explain this code in detail:
`python
{target_chunk['content']}
`

Provide:
1. Purpose: What does this function do?
2. Parameters: Explain each parameter
3. Return Value: What does it return?
4. Logic: Step-by-step explanation
5. Dependencies: What does it depend on?
6. Example Usage: How to use it?
"""
        
        explanation = self.generator.client.chat.completions.create(
            model=self.generator.model,
            messages=[
                {"role": "system", "content": "You are a code explanation expert. Be clear and concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
        ).choices[0].message.content
        
        return {
            "function_name": function_name,
            "file_path": target_chunk.get("metadata", {}).get("file_path", "unknown"),
            "code": target_chunk["content"],
            "explanation": explanation,
            "start_line": target_chunk.get("metadata", {}).get("start_line"),
            "end_line": target_chunk.get("metadata", {}).get("end_line"),
        }
    
    def find_usages(self, name: str) -> Dict[str, Any]:
        """Find all usages of a function, class, or variable."""
        
        results = self.retriever.search(name, top_k=20)
        
        usages = {
            "definition": None,
            "imports": [],
            "calls": [],
            "references": [],
        }
        
        for r in results:
            content = r.get("content", "")
            meta = r.get("metadata", {})
            
            info = {
                "file": meta.get("file_path", "unknown"),
                "line": meta.get("start_line", 0),
                "type": meta.get("chunk_type", "unknown"),
                "name": meta.get("name", ""),
                "snippet": content[:200],
            }
            
            # Categorize
            if meta.get("name") == name:
                usages["definition"] = info
            elif f"import {name}" in content or f"from" in content and name in content:
                usages["imports"].append(info)
            elif f"{name}(" in content:
                usages["calls"].append(info)
            else:
                usages["references"].append(info)
        
        return {
            "name": name,
            "total_usages": len(results),
            "usages": usages,
        }
    
    def find_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar code patterns in the codebase."""
        
        results = self.retriever.search(code_snippet, top_k=top_k)
        
        similar = []
        for r in results:
            meta = r.get("metadata", {})
            similar.append({
                "file": meta.get("file_path", "unknown"),
                "name": meta.get("name", "unknown"),
                "type": meta.get("chunk_type", "unknown"),
                "similarity_score": r.get("score", 0),
                "code": r.get("content", "")[:500],
                "line": meta.get("start_line", 0),
            })
        
        return similar
    
    def generate_documentation(self, file_path: str) -> str:
        """Generate documentation for a file."""
        
        # Get all chunks from this file
        results = self.retriever.search(file_path, top_k=20)
        
        file_chunks = [r for r in results if r.get("metadata", {}).get("file_path") == file_path]
        
        if not file_chunks:
            return f"No code found for file: {file_path}"
        
        # Build code summary
        code_parts = []
        for chunk in file_chunks:
            meta = chunk.get("metadata", {})
            code_parts.append(f"### {meta.get('chunk_type', 'code').title()}: {meta.get('name', 'unnamed')}\n`python\n{chunk['content'][:500]}\n`")
        
        code_summary = "\n\n".join(code_parts[:10])
        
        prompt = f"""Generate professional documentation for this Python file.

File: {file_path}

Code:
{code_summary}

Generate:
1. Module Overview (what this file does)
2. Classes (list and describe each class)
3. Functions (list and describe each function)
4. Dependencies (what it imports)
5. Usage Example

Format as Markdown.
"""
        
        docs = self.generator.client.chat.completions.create(
            model=self.generator.model,
            messages=[
                {"role": "system", "content": "You are a technical documentation writer. Be clear and professional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
        ).choices[0].message.content
        
        return docs
    
    def analyze_codebase(self) -> Dict[str, Any]:
        """Get high-level analysis of the entire codebase."""
        
        # Get all chunks
        all_results = self.retriever.search("", top_k=100)
        
        stats = {
            "total_chunks": len(all_results),
            "files": set(),
            "classes": [],
            "functions": [],
            "by_type": {},
        }
        
        for r in all_results:
            meta = r.get("metadata", {})
            file_path = meta.get("file_path", "")
            chunk_type = meta.get("chunk_type", "unknown")
            name = meta.get("name", "")
            
            stats["files"].add(file_path)
            
            if chunk_type not in stats["by_type"]:
                stats["by_type"][chunk_type] = 0
            stats["by_type"][chunk_type] += 1
            
            if chunk_type == "class" and name:
                stats["classes"].append({"name": name, "file": file_path})
            elif chunk_type in ["function", "method"] and name:
                stats["functions"].append({"name": name, "file": file_path})
        
        stats["files"] = list(stats["files"])
        stats["total_files"] = len(stats["files"])
        
        return stats
    
    def suggest_improvements(self, code: str) -> str:
        """Suggest improvements for given code."""
        
        prompt = f"""Review this code and suggest improvements:
`python
{code}
`

Provide:
1. Code Quality Issues
2. Performance Improvements
3. Security Concerns
4. Best Practices Violations
5. Refactoring Suggestions

Be specific and provide examples.
"""
        
        suggestions = self.generator.client.chat.completions.create(
            model=self.generator.model,
            messages=[
                {"role": "system", "content": "You are a senior code reviewer. Be constructive and specific."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        ).choices[0].message.content
        
        return suggestions
