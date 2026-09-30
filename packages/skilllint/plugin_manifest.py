"""Dependency-light Claude plugin manifest loading.

This module owns cached decoding of ``.claude-plugin/plugin.json`` so low-level
classification and boundary ingestion do not depend on scan/CLI orchestration.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path


@functools.cache
def load_plugin_json(plugin_root: Path) -> dict | None:
    """Load and cache ``.claude-plugin/plugin.json`` for a plugin root.

    Args:
        plugin_root: Directory containing ``.claude-plugin/plugin.json``.

    Returns:
        Parsed mapping, or None when the manifest is missing, unreadable,
        invalid JSON, or not a JSON object.
    """
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


# Compatibility name retained by scan_runtime and existing tests.
_load_plugin_json = load_plugin_json

__all__ = ["load_plugin_json"]
