# Modernization Report: auto_sync_manifests.py

**File**: `/home/user/agentskills-linter/packages/skilllint/auto_sync_manifests.py`
**Date**: 2026-03-13
**Target**: Python 3.11+

## Modernization Opportunities

### 1. FURB101: Use Direct Path Read Methods (MEDIUM)
Five instances of `with path.open() as f: data = f.read()` should use `path.read_bytes()` (for msgspec) or `path.read_text()`.

### 2. Unused Import Cleanup (LOW)
`tempfile` is imported but never used -- dead code from a prior refactor.

### 3. Module-Level Side Effects (MEDIUM)
`sys.stdout.reconfigure()` at module scope (lines 40-43) executes on import. Guard this behind `if __name__ == "__main__"` or move to the CLI entry point function to avoid side effects when the module is imported as a library.

### 4. File Size / Single Responsibility (LOW)
At 1300+ lines, the module combines CLI parsing, git diff analysis, manifest CRUD, version bumping, and reconciliation. Consider decomposing into submodules (e.g., `_version_bump.py`, `_reconcile.py`, `_git_helpers.py`).

## Already Modern

- Uses `from __future__ import annotations` (PEP 563).
- Uses `StrEnum` would be applicable if enums are introduced.
- Uses `pathlib.Path` throughout.
- Uses `msgspec.json` for fast JSON serialization.
- Uses native generic syntax (`dict[str, ...]`, `list[...]`).
- Uses union syntax (`str | None`).
