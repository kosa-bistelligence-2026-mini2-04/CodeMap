def clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def is_even(n: int) -> bool:
    return n % 2 == 0
