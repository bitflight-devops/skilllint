# Code Smell Report: adapters/claude_code/adapter.py

**File**: `/home/user/agentskills-linter/packages/skilllint/adapters/claude_code/adapter.py`
**Date**: 2026-03-13

## Ruff Findings
All checks passed. No issues found.

## Mypy Findings
Only `import-not-found` for `msgspec` (missing type stubs). No logic errors.

## Shebang Analysis
- **Current shebang**: None
- **Execute bit**: Not set
- **Rule**: Rule 4 (non-executable library module).
- **Verdict**: CORRECT.

## Code Quality Observations

### Potential Logic Issue (MEDIUM)
- **Line 66**: `self.get_schema("plugin")` is called in `validate()`, but the `get_schema()` method (line 35) checks for `file_type in file_types` where `file_types` comes from `schema.get("file_types", {})`. If the schema does not have a `"plugin"` key in `file_types`, this falls through to the `file_type == "plugin_json"` check (line 42), which also won't match `"plugin"`. This means `validate()` may always return `[]` for JSON files. Verify that the schema actually contains a `"plugin"` entry in `file_types`.

### Unused Import in Production Path (LOW)
- **Line 12**: `import msgspec.json` is used only in `validate()`. This is fine but could be a lazy import if startup time matters.

### Missing Protocol Compliance Annotation (LOW)
- `ClaudeCodeAdapter` appears to implement `PlatformAdapter` protocol but does not inherit from it or declare compliance. Consider adding explicit `PlatformAdapter` as a base class or adding a type assertion.
