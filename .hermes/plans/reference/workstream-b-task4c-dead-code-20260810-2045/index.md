status: PASS

## Result
Deleted dead AS001/AS002 and SK001/SK002/SK003 rule implementations, decorators, metadata, and exports. Updated stale production descriptions; retained active AS003/AS006-AS009 and SK004-SK009 paths.

## Scope and changed paths
- `packages/skilllint/rules/as_series.py`
- `packages/skilllint/rules/sk_series.py`
- `packages/skilllint/plugin_validator.py`

## Validation
- `uv sync` — PASS
- `uv run pytest packages/skilllint/tests/ -q --no-cov` — PASS: 1135 passed, 1 skipped, 1 xfailed
- `uv run ruff check --no-fix packages/` — PASS
- `uv run ty check packages/` — PASS
- Production grep for deleted codes — no executable references; one generic historical docstring example remains in `plugin_validator.py:5854`.

## Decisions and follow-ups
- Outright removal per owner decision; no stubs or compatibility aliases.
- Existing unrelated untracked Task 3 report directory was left untouched.

## Linked detail
- None.
