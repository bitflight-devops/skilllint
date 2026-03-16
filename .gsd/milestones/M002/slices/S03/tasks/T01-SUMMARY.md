---
id: T01
parent: S03
milestone: M002
status: complete
completed_at: 2026-03-15T20:55:00-04:00
---

# T01: Add plugin.json Component Detection

**Status:** complete

## What Happened

Added functions to read and parse plugin.json manifests:

1. Created `PluginManifest` dataclass to hold parsed manifest data (name, agents, commands, skills, hooks)
2. Created `read_plugin_manifest()` function to read and parse plugin.json
3. Created `PROVIDER_DIR_NAMES` frozenset for provider directory detection
4. Created `detect_discovery_mode()` function to determine which mode to use

**Detection logic:**
- MANIFEST: plugin.json exists AND has explicit component arrays
- AUTO: plugin.json exists but no explicit arrays, OR no plugin.json in plain directory
- STRUCTURE: directory name is .claude, .agent, .agents, .gemini, or .cursor

## Verification

- Imports work: `from skilllint.scan_runtime import detect_discovery_mode, read_plugin_manifest, ...`
- Existing tests pass