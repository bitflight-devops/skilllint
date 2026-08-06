# PR #95 review-fix report

- Branch: `feat/issue-88-skill-folder-scanning`
- Scope: `scan_runtime.py`, `plugin_validator.py`, `test_cli.py`, `test_markdown_token_counter.py`
- Codex P1 fixes: skill-folder ignore matching now uses concrete `SKILL.md`; `--platform` normalizes skill-folder targets before adapter validation.
- CodeRabbit fixes: plugin test drives plugin-root manifest discovery and asserts `SKILL.md`; missing-link regression asserts failure and one target; token test includes nested markdown and asserts exact complete output.
- Validation: `uv run pytest --no-cov packages/skilllint/tests/test_cli.py packages/skilllint/tests/test_markdown_token_counter.py packages/skilllint/tests/test_scan_context.py` — 139 passed, 1 skipped.
- Focused platform/regression tests: 11 passed.
- Lint/format: targeted Ruff check passed; targeted Ruff format check passed; `git diff --check` passed.
- Skipped findings: none.
- Commit: recorded in the delivery summary; verify with `git rev-parse HEAD`.

## Review-finding index

| Finding | Status | Evidence |
|---|---|---|
| Codex P1: ignore matching loses concrete SKILL.md | Fixed | `_ignore_path()` in `scan_runtime.py` |
| Codex P1: platform path bypasses folder normalization | Fixed | platform branch in `plugin_validator.py` |
| CodeRabbit: plugin-contained test bypasses discovery | Fixed | `test_plugin_contained_skill_folder_validates` |
| CodeRabbit: valid-link test is vacuous | Fixed | missing-link regression in `test_cli.py` |
| CodeRabbit: token test truncates tabbed output | Fixed | exact output assertion with nested resource |
