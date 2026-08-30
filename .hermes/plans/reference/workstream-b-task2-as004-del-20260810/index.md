# Workstream B Task 2 — AS004 deletion

status: PASS

## Result
AS004 was deleted outright from the executable rule/error-code surface. Parser failures now remain FM002-owned; the focused parser test was flipped from xfail to a passing assertion.

## Scope and changed paths
Removed AS004 implementation, registry metadata, enum/alias/emission paths, parser warning construction, obsolete tests, and documentation references.

Changed paths:
- packages/skilllint/rules/as_series.py
- packages/skilllint/rules/pa_series.py
- packages/skilllint/plugin_validator.py
- packages/skilllint/limits.py
- packages/skilllint/tests/test_as_series.py
- packages/skilllint/tests/test_external_scan_proof.py
- packages/skilllint/tests/test_provider_validation.py
- packages/skilllint/tests/test_rule_deduplication.py
- packages/skilllint/tests/test_rule_truth.py
- plugins/agentskills-skilllint/skills/skilllint/SKILL.md
- plugins/agentskills-skilllint/skills/skilllint/references/rule-catalog.md

## Validation
- `uv sync` — PASS
- `uv run pytest packages/skilllint/tests/ -q --no-cov` — PASS: 1136 passed, 1 skipped, 5 xfailed
- `uv run ruff check --no-fix packages/` — PASS
- `uv run ty check packages/` — PASS
- `git diff --check` — PASS
- Repository executable-source search — PASS: no AS004 emission or ErrorCode reference remains; only the explicit regression assertion remains.

## Decisions and follow-ups
The explicit owner decision was followed: no deprecated AS004 stub or alias remains. Historical planning/audit documents were not rewritten. No additional report files.

## Links
None.
