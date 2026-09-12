"""Platform adapter registry.

load_adapters() discovers all registered adapters via the 'skilllint.adapters'
entry_points group, including bundled adapters and third-party extensions.

matches_file() checks whether a PurePath matches any of an adapter's path patterns.
"""

from __future__ import annotations

import importlib.metadata
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skilllint.adapters.protocol import PlatformAdapter

__all__ = ["load_adapters", "matches_file"]


def load_adapters() -> list[PlatformAdapter]:
    """Discover and instantiate all registered platform adapters.

    Returns a list of PlatformAdapter instances from all entry_points
    registered under the 'skilllint.adapters' group. Bundled adapters
    are registered in pyproject.toml; third-party adapters register
    via their own pyproject.toml without modifying core.

    Returns:
        List of instantiated PlatformAdapter objects.
    """
    eps = importlib.metadata.entry_points(group="skilllint.adapters")
    adapters: list[PlatformAdapter] = []
    for ep in eps:
        adapter_cls = ep.load()
        adapters.append(adapter_cls())
    return adapters


def matches_file(adapter: PlatformAdapter, path: pathlib.PurePath) -> bool:
    """Return True if the given path matches any of the adapter's path_patterns().

    Uses PurePath.match() for glob pattern matching.

    Args:
        adapter: A PlatformAdapter instance.
        path: The file path to check.

    Returns:
        True if path matches at least one pattern, False otherwise.
    """

    def pattern_parts_match(path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]) -> bool:
        if not pattern_parts:
            return not path_parts
        if pattern_parts[0] == "**":
            return any(
                pattern_parts_match(path_parts[index:], pattern_parts[1:]) for index in range(len(path_parts) + 1)
            )
        return (
            bool(path_parts)
            and pathlib.PurePath(path_parts[0]).match(pattern_parts[0])
            and pattern_parts_match(path_parts[1:], pattern_parts[1:])
        )

    def pattern_matches(pattern: str) -> bool:
        if "/" not in pattern:
            return path.match(pattern)
        return pattern_parts_match(path.parts, tuple(pattern.split("/")))

    return any(pattern_matches(pattern) for pattern in adapter.path_patterns())
