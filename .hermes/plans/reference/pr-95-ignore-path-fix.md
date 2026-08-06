# PR #95: normalized ignore-path fix

## Finding
`run_validation_loop` passed folder targets to `_build_gitignore_set` but checked the concrete `SKILL.md` path via `_ignore_path`, so gitignored skill folders could be validated instead of skipped.

## Fix
Build the ignored set from `_ignore_path(path)` for every expanded target. This preserves direct-file targets and keeps folder targets represented by their direct `SKILL.md`; validation still receives the original folder path.

## Call flow
`plugin_validator` expands targets and calls `run_validation_loop`; its local `_should_skip` performs pattern/gitignore checks, and the loop passes `_ignore_path(path)` into it.

## Verification
- `uv run pytest packages/skilllint/tests/test_scan_runtime.py -q --no-cov` — 28 passed
- `uv run ruff check ...` and `uv run ruff format --check ...` — passed
- `uv run ty check packages/skilllint/scan_runtime.py packages/skilllint/tests/test_scan_runtime.py` — passed
- `prek run --files packages/skilllint/scan_runtime.py packages/skilllint/tests/test_scan_runtime.py` — passed
- `git diff --check` — passed

## Commit
The final commit is available from `git rev-parse HEAD` in this worktree.

## Changed paths
- `packages/skilllint/scan_runtime.py`
- `packages/skilllint/tests/test_scan_runtime.py`

## Scope
No merge performed; only the bounded ignore-path fix and its focused regression test were changed.

## Durable index
This file is the durable report index for the fix and verification evidence.
