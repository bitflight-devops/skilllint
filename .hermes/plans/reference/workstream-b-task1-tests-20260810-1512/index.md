# Workstream B Task 1 — tests-first

status: PASS

Focused one-owner expectations were added for malformed names, directory mismatch, missing descriptions, body thresholds, and parser failures. All six parameterized/assertion cases are marked expected-failure (`xfail(strict=False)`) because the current pre-consolidation implementation still emits duplicate/retired findings; assertions remain strict and are not weakened.

## Scope and changed paths

- Added: `packages/skilllint/tests/test_rule_deduplication.py`
- Production code, registry, enum, and series modules: none changed.

## Validation

- `uv sync` — PASS
- `uv run pytest packages/skilllint/tests/test_rule_deduplication.py -q --no-cov` — PASS; `6 xfailed in 2.11s`
- `uv run ruff check --no-fix packages/skilllint/tests/test_rule_deduplication.py` — PASS
- `uv run ty check packages/` — PASS (`All checks passed!`)
- `git diff --check` — PASS

## Expected failures and rationale

- Invalid name: current output includes AS001, duplicate FM010, SK001/SK002, and AS002; target is exactly one FM010 syntax finding.
- Valid name in wrong directory: target is only AS002 directory equality; current path also duplicates/overlaps name owners.
- Missing description: target is only FM001; current AS003 and quality checks may co-occur.
- Over-threshold body (warning and error thresholds): target is one SK006 or SK007; current AS005 duplicates it.
- Parser failure: target is one FM002; current parser path may emit retired AS004.

No blockers. Commit contains only the new focused test file.

## Linked detail

- None; this index contains the complete bounded report.
