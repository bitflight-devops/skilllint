---
phase: 01-package-structure
plan: 03
subsystem: testing
tags: [pre-commit, pytest, importlib, package-imports, migration]

# Dependency graph
requires:
  - phase: 01-package-structure/01-01
    provides: skilllint package installed with CLI entry points
  - phase: 01-package-structure/01-02
    provides: pluginlint alias, bundled schema, tests excluded from wheel

provides:
  - .pre-commit-hooks.yaml defining the skilllint pre-commit hook
  - All test files importing from skilllint.plugin_validator (package imports)
  - README.md migration guide from PEP 723 scripts to package

affects:
  - Phase 2 (schema validation) — test import pattern established
  - CI/CD pipeline — pre-commit hook definition available
  - External users — upgrade path documented

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test imports use from skilllint.plugin_validator import X, not file-path loading"
    - "Mocker patches use full path skilllint.plugin_validator.X"
    - "Pre-commit hooks defined in .pre-commit-hooks.yaml at repo root with language: python"

key-files:
  created:
    - .pre-commit-hooks.yaml
    - .planning/phases/01-package-structure/01-03-SUMMARY.md
  modified:
    - packages/skilllint/tests/conftest.py
    - packages/skilllint/tests/test_external_tools.py
    - packages/skilllint/tests/test_plugin_structure_validator.py
    - packages/skilllint/tests/test_plugin_registration_validator.py
    - packages/skilllint/tests/test_markdown_token_counter.py
    - packages/skilllint/tests/test_cli.py
    - packages/skilllint/tests/test_hook_validator.py
    - packages/skilllint/tests/test_hook_script_discovery.py
    - packages/skilllint/tests/test_reporters.py
    - packages/skilllint/tests/test_progressive_disclosure_validator.py
    - packages/skilllint/tests/test_token_counting.py
    - packages/skilllint/tests/test_skills_array_bugs.py
    - packages/skilllint/tests/test_frontmatter_validator.py
    - packages/skilllint/tests/test_description_validator.py
    - packages/skilllint/tests/test_namespace_reference_validator.py
    - packages/skilllint/tests/test_name_format_validator.py
    - packages/skilllint/tests/test_internal_link_validator.py
    - packages/skilllint/tests/test_complexity_validator.py
    - README.md

key-decisions:
  - "All 17 test files updated from sys.path.insert + from plugin_validator import to from skilllint.plugin_validator import — conftest.py no longer acts as import gateway"
  - "_GIT_METADATA_MODULE constant in test_plugin_registration_validator.py updated to full path skilllint.plugin_validator._generate_plugin_metadata"
  - "ruff (via pre-commit lint hook) auto-removes unused imports — conftest.py no longer contains import skilllint.plugin_validator because it has no direct references; test files import directly"

patterns-established:
  - "Package import pattern: from skilllint.plugin_validator import X (not file-path loading)"
  - "Mocker patch path pattern: mocker.patch('skilllint.plugin_validator.X')"
  - "Pre-commit hook definition: language: python, entry: skilllint, types_or: [markdown, json, yaml], pass_filenames: true"

requirements-completed: [PKG-05]

# Metrics
duration: 8min
completed: 2026-03-03
---

# Phase 1 Plan 3: Pre-commit Hook, Test Import Migration, and README Migration Summary

**.pre-commit-hooks.yaml added, all 17 test files migrated from sys.path.insert/importlib to package imports, and README documents PEP 723 to package upgrade path — 529 tests passing**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-03T15:31:55Z
- **Completed:** 2026-03-03T15:40:22Z
- **Tasks:** 3
- **Files modified:** 21

## Accomplishments

- Created `.pre-commit-hooks.yaml` at repo root with valid YAML and correct pre-commit hook fields (id: skilllint, language: python, entry: skilllint, types_or: [markdown, json, yaml], pass_filenames: true)
- Removed `importlib.util.spec_from_file_location` block from `conftest.py` — all 17 test files now import directly from `skilllint.plugin_validator` using standard package imports
- Updated all `mocker.patch("plugin_validator.X")` calls to `mocker.patch("skilllint.plugin_validator.X")` across test_external_tools.py, test_plugin_structure_validator.py, and test_plugin_registration_validator.py (including `_GIT_METADATA_MODULE` constant)
- Added "Migration from PEP 723 scripts" section to README.md covering CLI upgrade and pre-commit hook migration
- All 529 tests pass (up from 521 baseline)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .pre-commit-hooks.yaml** - `de5bbe6` (chore)
2. **Task 2: Update conftest.py + fix mocker patch paths** - `a560585` (feat)
3. **Task 3: Document PEP 723 migration in README.md** - `e8aa273` (docs)

**Plan metadata:** (docs commit pending)

## Files Created/Modified

- `.pre-commit-hooks.yaml` - Pre-commit hook definition for skilllint
- `packages/skilllint/tests/conftest.py` - Removed spec_from_file_location block; test files now import directly
- `packages/skilllint/tests/test_external_tools.py` - Migrated to from skilllint.plugin_validator import; 54 mocker.patch paths updated
- `packages/skilllint/tests/test_plugin_structure_validator.py` - Migrated import; 2 mocker.patch paths updated
- `packages/skilllint/tests/test_plugin_registration_validator.py` - Migrated import; _GIT_METADATA_MODULE constant updated
- `packages/skilllint/tests/test_markdown_token_counter.py` - Migrated to import skilllint.plugin_validator as plugin_validator
- `packages/skilllint/tests/test_cli.py` - Migrated to import skilllint.plugin_validator as plugin_validator
- 12 additional test files - Migrated from sys.path.insert + from plugin_validator import to from skilllint.plugin_validator import
- `README.md` - Added Migration from PEP 723 scripts section

## Decisions Made

- `conftest.py` no longer contains `import skilllint.plugin_validator` — ruff auto-removes unused imports and the module has no direct references in conftest.py; test files import directly. This is the correct state.
- `_GIT_METADATA_MODULE` module-level constant updated to full path rather than patching at call sites — keeps patch target consistent with module location.

## Phase 1 ROADMAP.md Success Criteria

All 5 Phase 1 success criteria are satisfied:

1. **`skilllint --help` exits 0** — verified with installed wheel
2. **`agentlint --help` exits 0** — verified with installed wheel
3. **`pluginlint --help` exits 0** — verified with installed wheel
4. **`skillint --help` exits 0** — verified with installed wheel
5. **`from skilllint import load_bundled_schema; load_bundled_schema('claude_code')['platform']` returns `'claude_code'`** — verified

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] All 17 test files needed import updates, not just conftest.py**

- **Found during:** Task 2 (Update conftest.py to import from package)
- **Issue:** The old conftest.py registered `plugin_validator` in `sys.modules` so bare `from plugin_validator import X` imports worked in all test files. Removing that registration broke all 17 test files.
- **Fix:** Updated all 17 test files to use `from skilllint.plugin_validator import X` or `import skilllint.plugin_validator as plugin_validator`. Removed `sys.path.insert` blocks from all affected files. Updated all mocker.patch paths.
- **Files modified:** 17 test files (listed in Files Created/Modified)
- **Verification:** 529 tests passing, 0 failures
- **Committed in:** `a560585` (Task 2 commit)

**2. [Rule 1 - Bug] _GIT_METADATA_MODULE constant needed path update**

- **Found during:** Task 2, running tests after import migration
- **Issue:** `_GIT_METADATA_MODULE = "plugin_validator._generate_plugin_metadata"` in test_plugin_registration_validator.py caused 7 test failures — patch target did not match actual module location
- **Fix:** Updated constant to `"skilllint.plugin_validator._generate_plugin_metadata"`
- **Files modified:** `packages/skilllint/tests/test_plugin_registration_validator.py`
- **Verification:** All 7 previously-failing tests now pass
- **Committed in:** `a560585` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes were required consequences of the planned migration. No scope creep.

## Issues Encountered

- ruff lint hook auto-removes unused imports on every Edit operation — when adding `import skilllint.plugin_validator as plugin_validator` to conftest.py, ruff removed it because conftest.py has no direct references to `plugin_validator`. This is correct behavior; the fix was to update each test file directly instead of routing through conftest.py.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 complete: all 4 CLI entry points active, bundled schema accessible, pre-commit hook defined, tests use package imports, README documents migration path
- Phase 2 (schema validation) can proceed with confidence that the package install and test infrastructure are fully correct
- No blockers

---
*Phase: 01-package-structure*
*Completed: 2026-03-03*
