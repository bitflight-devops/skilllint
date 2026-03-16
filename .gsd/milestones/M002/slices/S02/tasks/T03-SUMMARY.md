---
id: T03
parent: S02
milestone: M002
status: complete
completed_at: 2026-03-15T20:50:00-04:00
---

# T03: Add Ownership Routing Tests

**Status:** complete

## What Happened

Created `test_ownership_routing.py` with 8 tests:

### TestValidatorOwnership (3 tests)
- `test_schema_validators_have_schema_ownership` - verifies schema validators are marked SCHEMA
- `test_lint_validators_have_lint_ownership` - verifies lint validators are marked LINT
- `test_all_known_validators_mapped` - verifies all validators have ownership entries

### TestValidatorConstraintScopes (5 tests)
- `test_all_validators_have_constraint_scopes` - verifies all validators have scope mappings
- `test_filter_with_shared_only` - verifies filtering works with "shared" scope
- `test_filter_with_provider_specific_only` - verifies filtering works with "provider_specific"
- `test_filter_excludes_mismatched_scopes` - verifies validators are excluded when scopes don't match
- `test_unknown_validator_included_by_default` - verifies unknown validators default to included

## Verification

```
$ uv run pytest packages/skilllint/tests/test_ownership_routing.py -v --no-cov
8 passed in 4.22s
```

All ownership routing tests pass, locking the ownership model as real behavior.