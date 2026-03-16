---
id: S02
parent: M002
milestone: M002
provides:
  - ValidatorOwnership enum (SCHEMA vs LINT)
  - VALIDATOR_OWNERSHIP mapping
  - VALIDATOR_CONSTRAINT_SCOPES mapping
  - get_validator_ownership() function
  - filter_validators_by_constraint_scopes() function
  - test_ownership_routing.py with 8 tests
  - Constraint scope filtering integrated into run_platform_checks() and validate_file()
requires:
  - slice: S01
    provides: scan_runtime.py with extracted seams
affects:
  - M002/S04 (builds on ownership model for rule classification)
  - M002/S05 (docs will describe ownership model)
key_files:
  - packages/skilllint/plugin_validator.py (ownership model additions)
  - packages/skilllint/tests/test_ownership_routing.py
key_decisions:
  - Defaulted all validators to support both "shared" and "provider_specific" scopes
  - Unknown validators default to LINT ownership (conservative)
  - Filtering uses set intersection (validator_scopes & constraint_scopes)
patterns_established:
  - Explicit ownership annotations for validators
  - Constraint scope filtering at the validation entry point
  - Tests lock ownership model as real behavior
observability_surfaces:
  - Debug logging shows constraint_scopes for each validation
  - Test output shows ownership classification results
drill_down_paths:
  - .gsd/milestones/M002/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S02/tasks/T03-SUMMARY.md
duration: 50m (T01:15m + T02:20m + T03:15m)
verification_result: passed
completed_at: 2026-03-15
---

# S02: Constraint Ownership Routing Cleanup

**Extracted explicit validator ownership model and constraint scope filtering with 8 passing tests.**

## What Happened

Slice S02 established explicit ownership boundaries between schema validation (hard failures) and lint-rule validation (warnings), and integrated provider constraint scope filtering into the validation pipeline.

### Task Execution

**T01: Map validator ownership** ✓
- Created `ValidatorOwnership` enum: SCHEMA (hard failures), LINT (warnings)
- Created `VALIDATOR_OWNERSHIP` mapping dict for all 12 validators
- Created `get_validator_ownership()` function

**T02: Add scope filtering to validation** ✓
- Created `VALIDATOR_CONSTRAINT_SCOPES` mapping (currently all support both scopes)
- Created `filter_validators_by_constraint_scopes()` function
- Integrated filtering into `run_platform_checks()` and `validate_file()`

**T03: Add ownership routing tests** ✓
- Created `test_ownership_routing.py` with 8 tests
- Tests verify ownership classification and constraint scope filtering

## Verification

```
$ uv run pytest packages/skilllint/tests/test_ownership_routing.py -v --no-cov
8 passed in 4.22s

$ uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov
35 passed, 1 skipped

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color
Exit: 0

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md --no-color
Exit: 1 (expected errors)
```

## Requirements Advanced

- R013 — Separate schema validation from lint-rule validation — **advanced** (ownership model extracted, S04 will classify hard failures)
- R014 — Clarify provider-specific vs shared rule ownership — **advanced** (constraint scope filtering in place)

## Requirements Validated

None yet. Ownership model is now in place for S04 to classify hard failures.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

1. **All validators currently support both scopes** — The constraint scope filtering infrastructure is in place, but all validators currently support both "shared" and "provider_specific". When a provider adds provider-specific constraints, the filtering will activate.

2. **Provider-specific rules not yet defined** — The infrastructure is ready, but no provider has defined provider-specific rules that would be filtered. This is expected as the next step.

## Follow-ups

1. **S04: Official-repo hard-failure truth pass** — Use ownership model to classify hard failures
2. **Provider-specific rules** — Add provider-specific validators as needed

## Files Created/Modified

- `packages/skilllint/plugin_validator.py` — Added ValidatorOwnership, VALIDATOR_OWNERSHIP, VALIDATOR_CONSTRAINT_SCOPES, and filtering functions
- `packages/skilllint/tests/test_ownership_routing.py` — New test module with 8 ownership routing tests