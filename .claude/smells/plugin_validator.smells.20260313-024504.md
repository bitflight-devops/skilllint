# Code Smell Report: plugin_validator.py

**File**: `/home/user/agentskills-linter/packages/skilllint/plugin_validator.py`
**Date**: 2026-03-13

## Ruff Findings (1 error)

### FURB101 - Redundant File Open Pattern (MEDIUM)
- **Line 3493**: `Path(plugin_json_path).open(encoding="utf-8")` followed by `f.read()` -- replace with `Path(plugin_json_path).read_bytes()` since `msgspec.json.decode()` accepts bytes directly.

## Mypy Findings (categorized, excluding missing stub errors)

### Type Narrowing Issues (HIGH, 3 locations)

1. **Line 1981**: `data["hooks"]` has type `YamlValue` but `validate_hook_script_references_in_hooks_dict` expects `dict[str, YamlValue]`. The guard on line 1979 checks `isinstance(data.get("hooks"), dict)` but mypy does not narrow `data["hooks"]` through `.get()` checks. Fix: assign `hooks = data["hooks"]` after the isinstance guard, or use an explicit cast.

2. **Line 3024**: `item.lstrip("./")` where `item` has type `YamlValue` (from iterating a `list[YamlValue]`). The list items could be non-strings. Fix: add `if isinstance(item, str)` guard or filter the list.

3. **Line 4063**: `group.get("hooks", [])` returns `YamlValue` which includes `int | float | None` -- not iterable. Fix: add isinstance check before iterating.

### Type Assignment Issue (MEDIUM)
- **Line 2957**: `metadata["author"] = author` assigns `dict[str, str]` to a slot typed as `YamlValue`. This is technically compatible but mypy flags it due to recursive type alias limitations. Consider narrowing the `metadata` dict's type annotation.

## Shebang Analysis

- **Current shebang**: None
- **Execute bit**: Not set
- **Rule**: Rule 4 (non-executable library module). This is a library module imported by other code.
- **Verdict**: CORRECT. No shebang needed.

## Structural Observations

- File is extremely large (4000+ lines). This is the most significant structural concern -- it combines validation logic, CLI interface, hook validation, auto-fix logic, and reporting in a single module.
- Module-level side effects: `sys.stdout.reconfigure()` at import time (lines 28-31) -- same concern as `auto_sync_manifests.py`.
- `_ADAPTERS` dict built at module level (line 85) -- runs `load_adapters()` on import, which may trigger filesystem operations.
