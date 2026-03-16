---
id: S02
parent: M002
milestone: M002
title: Constraint ownership routing cleanup
status: in_progress
depends: [S01]
risk: high
reviewers: []
---

# S02: Constraint Ownership Routing Cleanup

## Scope

This slice establishes explicit ownership boundaries between schema validation (hard failures) and lint-rule validation (warnings/findings), and makes provider-specific vs shared rule ownership filterable in code.

## What We Learned from S01

- `scan_runtime.py` extracted path discovery, filter expansion, and summary computation
- 24 seam boundary tests prove the extraction is active in runtime
- T01 (reporting extraction) was NOT completed - reporters still in plugin_validator.py
- `_run_validation_loop` kept in monolith due to deep coupling

## What S02 Must Solve

### R013: Schema vs Lint Boundary

Current state: `FrontmatterValidator`, `NameFormatValidator`, `DescriptionValidator`, `ComplexityValidator`, etc. are all mixed in `_get_validators_for_path()`. No explicit ownership model distinguishes:
- Schema-backed constraints (hard failures = exit code 1)
- Lint rules (warnings = exit code 0 with findings)

### R014: Provider-Specific vs Shared

Current state: `constraint_scopes` is retrieved in `validate_file()` but only logged, never used for filtering:
```python
constraint_scopes = primary_adapter.constraint_scopes()
_logger.debug("... constraint_scopes=%s", constraint_scopes)  # NOT USED
```

## Key Insight

The `PlatformAdapter` protocol already defines `constraint_scopes()` returning `{"shared", "provider_specific"}`. The schema already has field-level `constraint_scope` annotations. The gap is that code never actually filters validators/rules by scope.

## Execution Plan

1. **T01: Map validator ownership** — Document which validators are schema-backed vs lint rules; create explicit ownership tags
2. **T02: Add scope filtering to validation** — Use `constraint_scopes()` to filter which validators run based on provider
3. **T03: Add ownership tests** — Lock the ownership model with tests that verify schema vs lint behavior and provider filtering

## Success Criteria

After S02:
- Every validator has explicit ownership annotation (schema | lint)
- Provider-specific rules are filtered out when scanning with a provider that doesn't claim them
- Tests verify the ownership routing behavior
