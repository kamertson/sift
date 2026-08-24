"""Tiny Python module for mixed-language scan tests."""


def add(left: int, right: int) -> int:
    """Return the sum of *left* and *right*."""
    return left + right


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp *value* into the inclusive range [*low*, *high*]."""
    if low > high:
        raise ValueError("low must be <= high")
    return max(low, min(high, value))
