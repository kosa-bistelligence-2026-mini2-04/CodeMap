def route(method: str, path: str, handlers: dict) -> object | None:
    key = f"{method.upper()}:{path}"
    handler = handlers.get(key)
    if handler is None:
        alt_key = f"ANY:{path}"
        handler = handlers.get(alt_key)
    if handler is None:
        for pattern, h in handlers.items():
            m, p = pattern.split(":", 1)
            if m in (method.upper(), "ANY") and _match_pattern(p, path):
                handler = h
                break
    return handler


def _match_pattern(pattern: str, path: str) -> bool:
    parts_p = pattern.strip("/").split("/")
    parts_r = path.strip("/").split("/")
    if len(parts_p) != len(parts_r):
        return False
    for pp, rp in zip(parts_p, parts_r):
        if pp.startswith("{") and pp.endswith("}"):
            continue
        if pp != rp:
            return False
    return True
