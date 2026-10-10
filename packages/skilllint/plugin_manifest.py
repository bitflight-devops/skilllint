"""Dependency-light plugin manifest loading.

This module owns cached decoding of plugin manifests so low-level
classification and boundary ingestion do not depend on scan/CLI orchestration.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path


@functools.cache
def load_plugin_json(plugin_root: Path, manifest_path: str | None = None) -> dict | None:
    """Load and cache a JSON plugin manifest relative to its plugin root.

    Args:
        plugin_root: Plugin root directory.
        manifest_path: Adapter-declared manifest location; defaults to the Claude layout.

    Returns:
        Parsed mapping, or None when the manifest is missing, unreadable,
        invalid JSON, or not a JSON object.
    """
    path = plugin_root / (manifest_path if manifest_path is not None else ".claude-plugin/plugin.json")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


# Compatibility name retained by scan_runtime and existing tests.
_load_plugin_json = load_plugin_json

__all__ = ["load_plugin_json"]
