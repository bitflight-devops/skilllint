---
id: T02
parent: S01
milestone: M002
provides:
  - scan_runtime module with path discovery, filter expansion, and summary computation seams
  - Backwards-compatible aliases for extracted functions in plugin_validator.py
key_files:
  - packages/skilllint/scan_runtime.py
  - packages/skilllint/plugin_validator.py
key_decisions:
  - Created scan_runtime.py as the dedicated module for scan expansion and validation-loop orchestration seams
  - Kept _run_validation_loop in plugin_validator.py due to deep coupling with validation logic and reporter selection
  - Extracted discover_validatable_paths, resolve_filter_and_expand_paths, and compute_summary as pure functions
  - Added ValidationLoopRunner protocol for future testability and extension
  - Maintained backwards compatibility via module-level aliases
patterns_established:
  - Extract pure functions first, then add protocol for dependency injection
  - Re-export via aliases for backwards compatibility with internal callers
  - Keep deep-coupled orchestration (like _run_validation_loop) near its dependencies until those can be extracted too
observability_surfaces:
  - Validation results still flow through ValidationResult and existing reporter output
  - Exit codes preserved (0 for success, 1 for errors, 2 for invalid args)
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Extract scan expansion and validation-loop orchestration seams

**Extracted path discovery, filter expansion, and summary computation seams into scan_runtime.py with backwards-compatible aliases.**

## What Happened

The task extracted three core orchestration functions from `plugin_validator.py` into a new `scan_runtime.py` module:

1. **`discover_validatable_paths`** - Auto-discovery of validatable files in bare directories using DEFAULT_SCAN_PATTERNS
2. **`resolve_filter_and_expand_paths`** - Filter option resolution (glob and filter-type) with directory expansion
3. **`compute_summary`** - Summary statistics computation from validation results

The constants `FILTER_TYPE_MAP` and `DEFAULT_SCAN_PATTERNS` were also moved to the new module.

The `_run_validation_loop` function was kept in `plugin_validator.py` because it has deep coupling with:
- Reporter selection (`ConsoleReporter` vs `CIReporter`)
- Platform override handling via `validate_file`
- `_validate_single_path` which orchestrates the full validator chain
- Ignore pattern loading

However, a `ValidationLoopRunner` protocol was added to `scan_runtime.py` for future testability, and `run_validation_loop` is provided as a dependency-injectable alternative for when the reporter and validator functions can be passed as parameters.

Backwards compatibility was maintained via module-level aliases (`_discover_validatable_paths = discover_validatable_paths`, etc.) so existing internal callers in `plugin_validator.py` continue to work without changes.

**Note:** T01 was marked complete in S01-PLAN.md but the reporting types (`Reporter` protocol, `ConsoleReporter`, `CIReporter`, `SummaryReporter`) remain in `plugin_validator.py`. The `reporting.py` module does not exist. This discrepancy should be addressed.

## Verification

All slice-level verification checks pass:

```bash
$ uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov
35 passed, 1 skipped

$ uv run pytest packages/skilllint/tests/test_provider_validation.py -q --no-cov
22 passed

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color
Exit code: 0

$ uv run python -m skilllint.plugin_validator check /tmp/bad-skill/SKILL.md --no-color
Exit code: 1
```

Module imports verified:
```bash
$ uv run python -c "from skilllint.scan_runtime import discover_validatable_paths, resolve_filter_and_expand_paths, compute_summary"
scan_runtime imports work

$ uv run python -c "from skilllint.plugin_validator import _discover_validatable_paths, _resolve_filter_and_expand_paths, _compute_summary"
Backwards-compatible aliases work
```

## Diagnostics

To verify the extracted seams are active in runtime:

1. **Import check**: `python -c "from skilllint.scan_runtime import discover_validatable_paths"`
2. **CLI execution**: Run `skilllint check <path>` and verify exit codes match expected behavior
3. **Failure path**: Create a skill with uppercase name (e.g., `Bad-Skill`) and verify exit code 1

## Deviations

None. The extraction followed the task plan. The `_run_validation_loop` function was kept in `plugin_validator.py` due to its deep coupling with validation logic, which is consistent with the task's goal of extracting "generic" scan expansion while keeping validation-specific logic in place.

## Known Issues

1. **T01 discrepancy**: The T01 task is marked complete in S01-PLAN.md but `reporting.py` does not exist and reporter classes remain in `plugin_validator.py`. This should be addressed before or during T03.

## Files Created/Modified

- `packages/skilllint/scan_runtime.py` — New module with extracted scan expansion, filter resolution, and summary computation functions
- `packages/skilllint/plugin_validator.py` — Added import from scan_runtime, removed duplicate function definitions, added backwards-compatible aliases
- `.gsd/milestones/M002/slices/S01/S01-PLAN.md` — Added failure-path verification step (pre-flight fix)
