def analyze_ast(node: dict, depth: int = 0) -> dict:
    """Analyze an AST node recursively — high CC for fixture purposes."""
    kind = node.get("type", "unknown")
    result: dict = {"kind": kind, "depth": depth, "children": []}

    if kind == "module":
        for child in node.get("body", []):
            result["children"].append(analyze_ast(child, depth + 1))
    elif kind == "function":
        result["name"] = node.get("name")
        for stmt in node.get("body", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
    elif kind == "if":
        result["test"] = node.get("test")
        for stmt in node.get("body", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
        for stmt in node.get("orelse", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
    elif kind == "for":
        for stmt in node.get("body", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
        for stmt in node.get("orelse", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
    elif kind == "while":
        for stmt in node.get("body", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
    elif kind == "try":
        for stmt in node.get("body", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
        for handler in node.get("handlers", []):
            for stmt in handler.get("body", []):
                result["children"].append(analyze_ast(stmt, depth + 1))
        for stmt in node.get("finalbody", []):
            result["children"].append(analyze_ast(stmt, depth + 1))
    elif kind == "assign":
        result["targets"] = node.get("targets", [])
    elif kind == "return":
        result["value"] = node.get("value")
    elif kind == "expr":
        result["value"] = node.get("value")
    else:
        result["raw"] = node

    return result
