# Code Smell Report: auto_sync_manifests.py

**File**: `/home/user/agentskills-linter/packages/skilllint/auto_sync_manifests.py`
**Date**: 2026-03-13

## Ruff Findings (6 errors)

### F401 - Unused Import (HIGH)
- **Line 33**: `import tempfile` is imported but never used.
- **Fix**: Remove the unused import.

### FURB101 - Redundant File Open Pattern (MEDIUM, 5 instances)
- **Line 487**: `plugin_json_path.open()` followed by `f.read()` -- replace with `plugin_json_path.read_text(encoding="utf-8")` or `plugin_json_path.read_bytes()` for msgspec.
- **Line 544**: Same pattern with `plugin_json_path`.
- **Line 613**: Same pattern with `marketplace_json_path`.
- **Line 1157**: Same pattern with `marketplace_path`.
- **Line 1304**: Same pattern with `Path(".claude-plugin/marketplace.json")`.

Since `msgspec.json.decode()` accepts `bytes`, the idiomatic replacement is `msgspec.json.decode(path.read_bytes())` which avoids the encoding parameter entirely.

## Shebang Analysis

- **Current shebang**: `#!/usr/bin/env python3`
- **Execute bit**: Set (executable)
- **Rule**: Rule 2 (package executable) -- file is part of the `skilllint` installed package with dependencies managed by `pyproject.toml`.
- **Verdict**: CORRECT. The shebang and execute bit are appropriate. No PEP 723 inline metadata is needed since dependencies are managed at the package level.

## Structural Observations

- File is large (1300+ lines) serving as both a library module and a CLI entry point. Consider splitting CLI argument parsing from core sync logic.
- Module-level side effects: `sys.stdout.reconfigure()` runs at import time (lines 40-43), which can surprise importers who only need utility functions.
