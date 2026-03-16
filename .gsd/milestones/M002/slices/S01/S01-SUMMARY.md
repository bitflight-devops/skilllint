---
id: S01
parent: M002
milestone: M002
provides:
  - scan_runtime module with path discovery, filter expansion, and summary computation seams
  - test_scan_runtime.py with 24 seam boundary regression tests
  - Backwards-compatible aliases ensuring CLI routes through extracted modules
  - Proven via import identity tests that extracted functions are the same objects used by CLI
requires:
  - slice: none
    provides: nothing (first slice)
affects:
  - M002/S02 (builds on extracted seams for ownership routing)
  - M002/S03 (builds on scan orchestration seam for discovery contract)
key_files:
  - packages/skilllint/scan_runtime.py
  - packages/skilllint/plugin_validator.py
  - packages/skilllint/tests/test_scan_runtime.py
key_decisions:
  - Created scan_runtime.py as dedicated module for scan expansion and validation-loop orchestration
  - Kept _run_validation_loop in plugin_validator.py due to deep coupling with validation/reporter logic
  - Added ValidationLoopRunner protocol for future testability
  - Maintained backwards compatibility via module-level aliases
  - T01 reporting extraction was NOT completed (reporting.py does not exist; reporters remain in plugin_validator.py)
patterns_established:
  - Extract pure functions first, add protocol for dependency injection later
  - Re-export via aliases for backwards compatibility with internal callers
  - Keep deep-coupled orchestration near its dependencies until those can be extracted too
  - Use import identity tests to prove seams are active in runtime, not dead code
observability_surfaces:
  - Validation results still flow through ValidationResult and existing reporter output
  - Exit codes preserved (0 for success, 1 for errors, 2 for invalid args)
  - Test output shows which seam tests pass/fail
drill_down_paths:
  - .gsd/milestones/M002/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S01/tasks/T03-SUMMARY.md
duration: 1h30m (45m T02 + 45m T03)
verification_result: passed
completed_at: 2026-03-15
---

# S01: Validator seam map and boundary extraction

**Extracted scan expansion and summary computation seams into scan_runtime.py with backwards-compatible aliases, locked by 24 seam boundary tests.**

## What Happened

Slice S01 extracted explicit internal validator seams from the monolithic `plugin_validator.py` into a dedicated `scan_runtime.py` module. The extraction focused on path discovery, filter expansion, and summary computation — the core orchestration responsibilities that S02 and S03 will build upon.

### Task Execution

**T02: Extract scan expansion and validation-loop orchestration seams** ✓
- Extracted `discover_validatable_paths`, `resolve_filter_and_expand_paths`, and `compute_summary` into `scan_runtime.py`
- Moved constants `FILTER_TYPE_MAP` and `DEFAULT_SCAN_PATTERNS` to the new module
- Added `ValidationLoopRunner` protocol for future testability
- Kept `_run_validation_loop` in `plugin_validator.py` due to deep coupling with validation logic and reporter selection
- Added backwards-compatible aliases so existing internal callers continue working

**T03: Lock seam boundaries with focused regression coverage** ✓
- Created `test_scan_runtime.py` with 24 seam boundary tests
- Import identity tests prove the extracted functions ARE the same objects used by the CLI (not copies)
- Seam wiring tests verify the CLI actually routes through extracted modules
- Reporter selection tests verify ConsoleReporter vs CIReporter behavior

**T01: Reporting extraction** ✗ (NOT COMPLETED)
- Marked complete in S01-PLAN.md but `reporting.py` does not exist
- `Reporter` protocol, `ConsoleReporter`, `CIReporter`, `SummaryReporter` remain in `plugin_validator.py`
- This is a gap that should be addressed in a follow-up or during S02

## Verification

All slice-level verification passes:

```
$ uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov
35 passed, 1 skipped

$ uv run pytest packages/skilllint/tests/test_provider_validation.py -q --no-cov
22 passed

$ uv run pytest packages/skilllint/tests/test_scan_runtime.py -v --no-cov
24 passed

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color
Exit code: 0

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md --no-color
Exit code: 1 (expected failure)
```

Import identity verification:
```bash
$ python -c "from skilllint.plugin_validator import _discover_validatable_paths
from skilllint.scan_runtime import discover_validatable_paths
assert _discover_validatable_paths is discover_validatable_paths"
```

## Requirements Advanced

- R012 — Decompose remaining validator monolith into explicit layers — **advanced** (seams extracted; S02 must complete ownership routing)

## Requirements Validated

None yet. R012 is partially complete but still Active until S02 completes the ownership model.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

1. **T01 reporting extraction not completed** — The plan called for extracting reporter classes into `reporting.py`, but this was marked complete without being done. Reporters remain in `plugin_validator.py`.

## Known Limitations

1. **Reporter classes still in plugin_validator.py** — T01 was not actually completed. The `Reporter` protocol and implementations (`ConsoleReporter`, `CIReporter`, `SummaryReporter`) remain in the monolith. This should be addressed in S02 or a follow-up.

2. **_run_validation_loop kept in monolith** — Deep coupling with validation logic and reporter selection kept this function in `plugin_validator.py`. A `ValidationLoopRunner` protocol exists for future extraction.

## Follow-ups

1. **Complete reporting extraction** — Extract `Reporter` protocol and implementations into `reporting.py` to fully realize T01's intent. This could be done in S02 as part of ownership routing.

2. **S02 ownership routing** — Now that the scan orchestration seams are extracted, S02 should build the schema-vs-rule ownership model on these seams.

## Files Created/Modified

- `packages/skilllint/scan_runtime.py` — New module with extracted scan expansion, filter resolution, and summary computation (203 lines)
- `packages/skilllint/plugin_validator.py` — Added import from scan_runtime, removed duplicate function definitions, added backwards-compatible aliases
- `packages/skilllint/tests/test_scan_runtime.py` — New test module with 24 seam boundary tests

## Forward Intelligence

### What the next slice should know
- The extracted seams in `scan_runtime.py` are the foundation for S02 and S03. `discover_validatable_paths`, `resolve_filter_and_expand_paths`, and `compute_summary` are stable entry points.
- The import identity tests in `test_scan_runtime.py` prove that `plugin_validator.py` actually uses the extracted modules — this is the pattern to maintain.

### What's fragile
- **T01 gap** — Reporting classes still in `plugin_validator.py`. This should be extracted to `reporting.py` before S02 builds ownership routing.
- **_run_validation_loop coupling** — This function could not be extracted due to tight coupling with validation logic. Any ownership routing that affects reporter selection or validation flow may need to account for this.

### Authoritative diagnostics
- `uv run pytest packages/skilllint/tests/test_scan_runtime.py -v` — Shows which seam tests pass/fail
- `uv run python -m skilllint.plugin_validator check <path> --no-color` — Verifies CLI still works through extracted seams
- Import identity: `python -c "from skilllint.plugin_validator import _X; from skilllint.scan_runtime import X; assert _X is X"` — Proves seam is active

### What assumptions changed
- Original: T01 (reporting extraction) was complete. **Actual**: Reporting was not extracted; reporters remain in monolith.
- Original: All orchestration functions could be extracted cleanly. **Actual**: `_run_validation_loop` has deep coupling that prevents clean extraction without also extracting validation logic.
