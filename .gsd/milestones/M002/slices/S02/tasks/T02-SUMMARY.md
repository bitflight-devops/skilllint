---
id: T02
parent: S02
milestone: M002
status: complete
completed_at: 2026-03-15T20:45:00-04:00
---

# T02: Add Scope Filtering to Validation

**Status:** complete

## What Happened

Implemented constraint scope filtering so provider-specific validators can be filtered:

1. Created `VALIDATOR_CONSTRAINT_SCOPES` mapping dict (all validators currently support both "shared" and "provider_specific")
2. Created `get_validator_constraint_scopes()` function
3. Created `filter_validators_by_constraint_scopes()` function
4. Updated `run_platform_checks()` to filter validators by provider constraint scopes
5. Updated `validate_file()` to filter validators by provider constraint scopes

The infrastructure is in place. Currently all validators run for all providers since all support both scopes. When a provider adds provider-specific constraints, the filtering will activate.

## Key Code Changes

```python
# In run_platform_checks():
sk_validators = filter_validators_by_constraint_scopes(sk_validators, constraint_scopes)

# In validate_file():
sk_validators = filter_validators_by_constraint_scopes(sk_validators, constraint_scopes)
```

## Verification

- All tests pass (67 passed, 1 skipped)
- CLI validates correctly with filtered validators
- Provider constraint_scopes() is now used for actual filtering