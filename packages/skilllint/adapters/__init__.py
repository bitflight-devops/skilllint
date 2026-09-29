"""Platform adapter registry.

load_adapters() discovers all registered adapters via the 'skilllint.adapters'
entry_points group, including bundled adapters and third-party extensions.

matches_file() checks whether a PurePath matches any of an adapter's path patterns.
"""

from __future__ import annotations

from skilllint.adapters.protocol import (
    ALL_RULE_SERIES,
    PlatformAdapter,
    PlatformPluginDiscovery,
    PluginLayout,
)
from skilllint.adapters.registry import load_adapters, matches_file

__all__ = [
    "ALL_RULE_SERIES",
    "PlatformAdapter",
    "PlatformPluginDiscovery",
    "PluginLayout",
    "load_adapters",
    "matches_file",
]
