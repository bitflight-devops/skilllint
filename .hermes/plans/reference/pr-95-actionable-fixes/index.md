# PR #95 actionable fixes

- **Status:** PASS
- **Result:** Fixed both current-head actionable findings with the existing `_ignore_path` normalization helper: platform validation now receives `SKILL.md` for folder targets, and manifest skill declarations deduplicate folder/file aliases while preserving the first declared target.
- **Scope / changed paths:**
  - `packages/skilllint/scan_runtime.py`
  - `packages/skilllint/tests/test_scan_runtime.py`

## Validation

- `uv run --project /tmp/skilllint-slice2-20260806 pytest --no-cov packages/skilllint/tests/test_scan_runtime.py packages/skilllint/tests/test_cli.py packages/skilllint/tests/test_markdown_token_counter.py -q` — **104 passed, 1 skipped**.
- `uv run --project /tmp/skilllint-slice2-20260806 pytest --no-cov packages/skilllint/tests/test_scan_runtime.py -q` — **29 passed**.
- Ruff check — **passed**.
- Ty check — **passed**.
- `prek run --files packages/skilllint/scan_runtime.py packages/skilllint/tests/test_scan_runtime.py` — **passed**.
- `git diff --check` — **passed**.

## Decisions / follow-ups

No compatibility shim, new abstraction, or unrelated change added. The pre-existing `claude-review` infrastructure failure remains classified as expected and was not retried.

Links: none.

Commit and push are recorded after this report is created.

## Evidence

The focused regression covers platform callback normalization and duplicate manifest declarations (`skills/foo` plus `skills/foo/SKILL.md`).
