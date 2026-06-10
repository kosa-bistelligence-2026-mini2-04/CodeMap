import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import json

try:
    import networkx as nx
except ImportError:
    nx = None

from ..utils import logger


@dataclass
class ImportInfo:
    module: str
    names: List[str]
    is_relative: bool
    line_number: int


@dataclass
class FileNode:
    path: str
    imports: List[ImportInfo] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    

class DependencyGraphBuilder:
    
    def __init__(self):
        self.graph = None
        self.file_nodes: Dict[str, FileNode] = {}
        self.module_to_file: Dict[str, str] = {}
        
    def build_graph(self, files: List):
        if nx is None:
            logger.warning("NetworkX not installed")
            return None
            
        self.graph = nx.DiGraph()
        self.file_nodes = {}
        self.module_to_file = {}
        
        for file in files:
            if file.language != "python":
                continue
            self._process_file(file)
        
        for file_path, node in self.file_nodes.items():
            for imp in node.imports:
                resolved = self._resolve_import(imp, file_path)
                if resolved and resolved in self.file_nodes:
                    self.graph.add_edge(file_path, resolved)
                    self.file_nodes[resolved].imported_by.append(file_path)
        
        logger.info(f"Built dependency graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return self.graph
    
    def _process_file(self, file) -> None:
        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            return
            
        node = FileNode(path=file.path)
        
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Import):
                for alias in ast_node.names:
                    node.imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        is_relative=False,
                        line_number=ast_node.lineno
                    ))
                    
            elif isinstance(ast_node, ast.ImportFrom):
                module = ast_node.module or ""
                names = [alias.name for alias in ast_node.names]
                node.imports.append(ImportInfo(
                    module=module,
                    names=names,
                    is_relative=ast_node.level > 0,
                    line_number=ast_node.lineno
                ))
                
            elif isinstance(ast_node, ast.FunctionDef):
                node.functions.append(ast_node.name)
                
            elif isinstance(ast_node, ast.ClassDef):
                node.classes.append(ast_node.name)
        
        self.file_nodes[file.path] = node
        self.graph.add_node(file.path, functions=node.functions, classes=node.classes)
        
        module_name = file.path.replace("/", ".").replace("\\", ".").removesuffix(".py")
        self.module_to_file[module_name] = file.path
        
    def _resolve_import(self, imp: ImportInfo, source_file: str) -> Optional[str]:
        if imp.is_relative:
            source_dir = str(Path(source_file).parent)
            module_path = imp.module.replace(".", "/") if imp.module else ""
            resolved = f"{source_dir}/{module_path}.py" if module_path else None
            if resolved and resolved in self.file_nodes:
                return resolved
        else:
            module_parts = imp.module.split(".")
            for i in range(len(module_parts), 0, -1):
                test_module = ".".join(module_parts[:i])
                if test_module in self.module_to_file:
                    return self.module_to_file[test_module]
                test_path = "/".join(module_parts[:i]) + ".py"
                if test_path in self.file_nodes:
                    return test_path
        return None
    
    def get_dependencies(self, file_path: str) -> List[str]:
        if self.graph is None or file_path not in self.graph:
            return []
        return list(self.graph.successors(file_path))
    
    def get_dependents(self, file_path: str) -> List[str]:
        if self.graph is None or file_path not in self.graph:
            return []
        return list(self.graph.predecessors(file_path))
    
    def get_related_files(self, file_path: str, depth: int = 2) -> Set[str]:
        if self.graph is None or file_path not in self.graph:
            return set()
            
        related = set()
        current_level = {file_path}
        
        for _ in range(depth):
            next_level = set()
            for f in current_level:
                next_level.update(self.get_dependencies(f))
                next_level.update(self.get_dependents(f))
            related.update(next_level)
            current_level = next_level - related
            
        related.discard(file_path)
        return related
    
    def get_most_connected_files(self, top_n: int = 10) -> List[Tuple[str, int]]:
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return []
        degrees = [(node, self.graph.degree(node)) for node in self.graph.nodes()]
        return sorted(degrees, key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_entry_points(self) -> List[str]:
        if self.graph is None:
            return []
        return [node for node in self.graph.nodes() if self.graph.in_degree(node) == 0]
    
    def get_core_modules(self) -> List[str]:
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return []
        in_degrees = [(node, self.graph.in_degree(node)) for node in self.graph.nodes()]
        sorted_nodes = sorted(in_degrees, key=lambda x: x[1], reverse=True)
        return [node for node, degree in sorted_nodes if degree > 0][:10]
