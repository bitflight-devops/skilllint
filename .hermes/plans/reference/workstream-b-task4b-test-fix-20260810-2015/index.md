status: PASS

Updated legacy tests and the FM010 fixture to match the retired-rule owner decision: FM010 owns frontmatter name validation, SK008 owns directory syntax, and removed AS001/AS002/SK001-SK003 expectations. No production files were changed.

Scope and changed paths:
- packages/skilllint/tests/test_as_series.py
- packages/skilllint/tests/test_name_format_validator.py
- packages/skilllint/tests/test_provider_validation.py
- packages/skilllint/tests/test_cli.py
- packages/skilllint/tests/test_e2e_packaging.py
- packages/skilllint/tests/fixtures/providers/agentskills/failing-examples/FM010/fixture.toml

Validation:
- uv run pytest packages/skilllint/tests/ -q --no-cov: PASS (1135 passed, 1 skipped, 1 xfailed)
- uv run ruff check --no-fix packages/: PASS
- uv run ty check packages/: PASS
- git diff --check: PASS

Retired-test handling:
- Removed four obsolete AS001/AS002 test functions by making them non-collectable regression notes.
- Updated name validator, provider, CLI, packaging, and fixture assertions to FM010 or remaining active owners.

Follow-up: a production grep still finds legacy SK001-SK003 implementations in rules/sk_series.py; these are pre-existing production definitions outside this test-only slice and should be retired by the owning production-rule task.

Additional files: none.
