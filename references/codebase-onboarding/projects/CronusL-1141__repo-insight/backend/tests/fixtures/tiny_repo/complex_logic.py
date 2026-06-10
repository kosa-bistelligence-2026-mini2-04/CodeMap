def process_pipeline(data: list, config: dict) -> dict:
    """Data processing pipeline with deep nesting — high CC for fixture purposes."""
    results: list = []
    errors: list = []
    skipped: list = []

    mode = config.get("mode", "default")
    threshold = config.get("threshold", 0.5)
    strict = config.get("strict", False)

    for item in data:
        if item is None:
            skipped.append(item)
            continue

        if isinstance(item, dict):
            val = item.get("value")
            if val is None:
                if strict:
                    errors.append({"item": item, "reason": "missing value in strict mode"})
                else:
                    skipped.append(item)
                continue

            if mode == "numeric":
                if isinstance(val, (int, float)):
                    if val > threshold:
                        if val > threshold * 2:
                            results.append({"item": item, "level": "high"})
                        else:
                            results.append({"item": item, "level": "medium"})
                    else:
                        results.append({"item": item, "level": "low"})
                else:
                    errors.append({"item": item, "reason": "non-numeric in numeric mode"})
            elif mode == "text":
                if isinstance(val, str):
                    if len(val) > 100:
                        results.append({"item": item, "level": "long"})
                    elif len(val) > 10:
                        results.append({"item": item, "level": "medium"})
                    else:
                        results.append({"item": item, "level": "short"})
                else:
                    errors.append({"item": item, "reason": "non-text in text mode"})
            else:
                results.append({"item": item, "level": "default"})
        elif isinstance(item, (int, float)):
            if item > threshold:
                results.append({"item": item, "level": "above"})
            else:
                results.append({"item": item, "level": "below"})
        elif isinstance(item, str):
            results.append({"item": item, "level": "string"})
        else:
            errors.append({"item": item, "reason": "unsupported type"})

    return {"results": results, "errors": errors, "skipped": skipped}
