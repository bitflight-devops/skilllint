"""Shared helpers for benchmark scripts."""

from __future__ import annotations


def to_float(value: object) -> float | None:
    """Convert an arbitrary JSON value to float when possible.

    Returns:
        Parsed float value, or ``None`` when conversion is not possible.
    """
    # bool is a subclass of int; reject it explicitly to avoid converting
    # semantic flags into numeric benchmark values.
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return None
    return None
