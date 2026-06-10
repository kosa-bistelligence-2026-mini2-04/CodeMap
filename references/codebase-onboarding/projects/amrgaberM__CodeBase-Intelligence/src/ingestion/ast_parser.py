"""AST Parser for extracting code structure."""

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CodeElement:
    """Represents a code element (function, class, etc.)."""
    
    name: str
    element_type: str  # "function", "class", "method", "module"
    content: str  # The actual code
    docstring: Optional[str] = None
    
    # Location
    start_line: int = 0
    end_line: int = 0
    
    # Relationships
    parent: Optional[str] = None  # Parent class/module
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)  # Functions this element calls
    
    # Metadata
    metadata: Dict = field(default_factory=dict)


class PythonASTParser:
    """Parse Python files using AST to extract code structure."""
    
    def parse(self, content: str, file_path: str = "") -> List[CodeElement]:
        """Parse Python code and extract elements.
        
        Args:
            content: Python source code
            file_path: Path to the file (for metadata)
            
        Returns:
            List of CodeElement objects
        """
        elements = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            # Return entire file as single element if parsing fails
            return [CodeElement(
                name=file_path or "module",
                element_type="module",
                content=content,
                start_line=1,
                end_line=content.count("\n") + 1,
                metadata={"parse_error": str(e)}
            )]
        
        # Extract imports at module level
        module_imports = self._extract_imports(tree)
        
        # Process top-level elements
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                elements.append(self._process_function(node, content, module_imports))
            
            elif isinstance(node, ast.AsyncFunctionDef):
                elements.append(self._process_function(node, content, module_imports, is_async=True))
            
            elif isinstance(node, ast.ClassDef):
                elements.extend(self._process_class(node, content, module_imports))
        
        # If no elements found, return whole file
        if not elements:
            elements.append(CodeElement(
                name=file_path or "module",
                element_type="module",
                content=content,
                start_line=1,
                end_line=content.count("\n") + 1,
                imports=module_imports
            ))
        
        return elements
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all imports from AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return imports
    
    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract function calls from a node."""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        
        return list(set(calls))
    
    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from a node."""
        try:
            return ast.get_docstring(node)
        except:
            return None
    
    def _get_source_segment(
        self,
        content: str,
        node: ast.AST
    ) -> Tuple[str, int, int]:
        """Extract source code for a node."""
        lines = content.split("\n")
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        
        # Include decorators
        if hasattr(node, "decorator_list") and node.decorator_list:
            first_decorator = node.decorator_list[0]
            start_line = first_decorator.lineno
        
        # Extract lines (1-indexed to 0-indexed)
        source_lines = lines[start_line - 1:end_line]
        source = "\n".join(source_lines)
        
        return source, start_line, end_line
    
    def _process_function(
        self,
        node: ast.FunctionDef,
        content: str,
        module_imports: List[str],
        parent_class: Optional[str] = None,
        is_async: bool = False
    ) -> CodeElement:
        """Process a function definition."""
        source, start_line, end_line = self._get_source_segment(content, node)
        
        # Determine element type
        if parent_class:
            element_type = "method"
        else:
            element_type = "async_function" if is_async else "function"
        
        return CodeElement(
            name=node.name,
            element_type=element_type,
            content=source,
            docstring=self._get_docstring(node),
            start_line=start_line,
            end_line=end_line,
            parent=parent_class,
            imports=module_imports,
            calls=self._extract_calls(node),
            metadata={
                "args": [arg.arg for arg in node.args.args],
                "decorators": [
                    self._get_decorator_name(d) for d in node.decorator_list
                ],
                "is_async": is_async,
            }
        )
    
    def _process_class(
        self,
        node: ast.ClassDef,
        content: str,
        module_imports: List[str]
    ) -> List[CodeElement]:
        """Process a class definition."""
        elements = []
        
        # Get class source
        source, start_line, end_line = self._get_source_segment(content, node)
        
        # Create class element
        class_element = CodeElement(
            name=node.name,
            element_type="class",
            content=source,
            docstring=self._get_docstring(node),
            start_line=start_line,
            end_line=end_line,
            imports=module_imports,
            metadata={
                "bases": [self._get_base_name(b) for b in node.bases],
                "decorators": [
                    self._get_decorator_name(d) for d in node.decorator_list
                ],
            }
        )
        elements.append(class_element)
        
        # Process methods
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                elements.append(
                    self._process_function(
                        child, content, module_imports, parent_class=node.name
                    )
                )
            elif isinstance(child, ast.AsyncFunctionDef):
                elements.append(
                    self._process_function(
                        child, content, module_imports, 
                        parent_class=node.name, is_async=True
                    )
                )
        
        return elements
    
    def _get_decorator_name(self, node: ast.expr) -> str:
        """Get decorator name as string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "unknown"
    
    def _get_base_name(self, node: ast.expr) -> str:
        """Get base class name as string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown"


class GenericCodeParser:
    """Fallback parser for non-Python files."""
    
    def parse(self, content: str, file_path: str = "", language: str = "unknown") -> List[CodeElement]:
        """Parse code file as a single element.
        
        For non-Python files, we return the whole file as one element.
        Future: Add support for JavaScript, TypeScript, etc.
        """
        return [CodeElement(
            name=file_path or "module",
            element_type="module",
            content=content,
            start_line=1,
            end_line=content.count("\n") + 1,
            metadata={"language": language}
        )]


def get_parser(language: str):
    """Get appropriate parser for language."""
    if language == "python":
        return PythonASTParser()
    else:
        return GenericCodeParser()
