def parse_tokens(tokens: list[str]) -> list[dict]:
    result = []
    for token in tokens:
        if token.startswith("INT:"):
            result.append({"type": "int", "value": int(token[4:])})
        elif token.startswith("STR:"):
            result.append({"type": "str", "value": token[4:]})
        elif token.startswith("BOOL:"):
            val = token[5:].lower() == "true"
            result.append({"type": "bool", "value": val})
        elif token.startswith("NULL"):
            result.append({"type": "null", "value": None})
        elif token.startswith("FLOAT:"):
            result.append({"type": "float", "value": float(token[6:])})
        else:
            result.append({"type": "unknown", "value": token})
    return result


def tokenize(text: str) -> list[str]:
    return text.split()
