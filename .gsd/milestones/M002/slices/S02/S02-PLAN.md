# S02 Plan: Constraint Ownership Routing Cleanup

**Parent:** M002
**Status:** in_progress
**Risk:** high

## Tasks

- [x] **T01: Map validator ownership** `est:30m`
  > Document which validators are schema-backed (hard failures) vs lint rules. Create explicit ownership tags in code.

- [x] **T02: Add scope filtering to validation** `est:45m`
  > Use `constraint_scopes()` from PlatformAdapter to filter which validators run based on provider. Currently constraint_scopes is retrieved but never used for filtering.

- [x] **T03: Add ownership routing tests** `est:30m`
  > Lock the ownership model with tests that verify schema vs lint behavior separation and provider-specific filtering works correctly.

## Dependencies

- S01 (completed) — provides extracted scan_runtime.py seams that S02 builds on

## Notes

- T01 (reporting extraction) from S01 was NOT completed - reporters still in plugin_validator.py. This doesn't block S02.
- The PlatformAdapter protocol already has `constraint_scopes()` method - the gap is using it for filtering
- Schema validators currently mix with lint validators in `_get_validators_for_path()`

## Verification

- Tests pass for ownership routing
- Provider-specific rules filtered when scanning with mismatched provider
- Schema validators still produce hard failures
- Lint validators still produce warnings
