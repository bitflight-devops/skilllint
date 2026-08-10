# Workstream B Task 4 — name-format consolidation

status: PARTIAL

## Result
FM010 is now the sole emitted frontmatter name/equality owner in the default validation path; SK008 remains the directory convention owner. AS001/AS002 are no longer emitted by AS-series, and SK001–SK003 are removed from ErrorCode/RULE_REGISTRY decorators. Focused deduplication tests pass except the pre-existing xfail for Task 3 description ownership.

## Scope and changed paths
- packages/skilllint/plugin_validator.py
- packages/skilllint/rules/as_series.py
- packages/skilllint/rules/sk_series.py
- packages/skilllint/tests/test_rule_deduplication.py
- plugins/agentskills-skilllint/skills/skilllint/references/rule-catalog.md

## Validation
- `uv run pytest packages/skilllint/tests/test_rule_deduplication.py -q --no-cov` — 5 passed, 1 xfailed
- `uv run ruff check --no-fix packages/` — passed
- `uv run ty check packages/` — passed
- `git diff --check` — passed
- executable decorator search for AS001/AS002/SK001–SK003 — no matches

## Blockers, decisions, follow-ups
- Full suite was not run. Legacy unit tests still reference retired codes and require the planned breaking-change cleanup.
- The old helper bodies remain undecorated for compatibility with direct legacy imports; they have no active registry or emission path.

## Linked detail
None.
