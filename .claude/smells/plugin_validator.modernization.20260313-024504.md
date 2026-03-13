# Modernization Report: plugin_validator.py

**File**: `/home/user/agentskills-linter/packages/skilllint/plugin_validator.py`
**Date**: 2026-03-13
**Target**: Python 3.11+

## Modernization Opportunities

### 1. Type Narrowing with TypeGuard or Explicit Checks (HIGH)
Three mypy errors stem from `YamlValue` union type not being narrowed before use. The `YamlValue` TypeAlias is broad (`dict | list | str | int | float | bool | None`). Functions that operate on specific variants need explicit `isinstance` guards or TypeGuard helpers.

Recommended: Create a `_as_str_list(value: YamlValue) -> list[str]` helper that safely extracts string lists from YamlValue, returning empty list for non-list inputs.

### 2. FURB101: Direct Path Read (MEDIUM)
Line 3493: Replace `with Path(plugin_json_path).open(...) as f: msgspec.json.decode(f.read())` with `msgspec.json.decode(Path(plugin_json_path).read_bytes())`.

### 3. Module-Level Side Effects (MEDIUM)
- `sys.stdout.reconfigure()` at lines 28-31 should be guarded or deferred.
- `_ADAPTERS` initialization at line 85 triggers `load_adapters()` on import.

### 4. File Decomposition (LOW)
At 4000+ lines, consider extracting:
- `HookValidator` class into its own module
- CLI entry point (`app`, typer commands) into `cli.py`
- Auto-fix logic into `_autofix.py`
- Reporting/formatting logic into `_reporting.py`

### 5. Exception Notes (PEP 678) (LOW)
Several `except` blocks re-raise or return error strings. Where exceptions are re-raised, consider using `e.add_note()` to attach context rather than wrapping in new exceptions.

## Already Modern

- Uses `from __future__ import annotations`.
- Uses `StrEnum` (line 34).
- Uses native generics and union syntax throughout.
- Uses `TypeAlias` for `YamlValue`.
- Uses `Protocol` (line 37).
- Uses `Annotated` for typer CLI parameters.
- Uses `dataclass` for structured data.
- Uses `msgspec.json` for JSON handling.
