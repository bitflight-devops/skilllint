---
phase: 02-platform-adapters
plan: 02
subsystem: adapters
tags: [protocol, entry-points, importlib-metadata, as-series, rules, skill-validation]

requires:
  - phase: 02-01
    provides: TDD scaffold with test stubs for test_adapters.py and test_as_series.py

provides:
  - "@runtime_checkable PlatformAdapter Protocol with id(), path_patterns(), applicable_rules(), validate()"
  - "load_adapters() entry_points registry via importlib.metadata group='skilllint.adapters'"
  - "matches_file(adapter, path) utility using PurePath.match()"
  - "Stub adapter classes for claude_code, cursor, codex (Protocol-compliant, full impl in 02-04)"
  - "check_skill_md(path) AS001-AS006 rule engine returning list[dict]"
  - "AS_RULES dict mapping code to description for LSP hover and list_rules"

affects:
  - 02-04 (full ClaudeCodeAdapter/CursorAdapter/CodexAdapter implementations use Protocol contract)
  - 02-03 (validation pipeline uses check_skill_md and load_adapters)
  - 04-lsp (AS_RULES dict used for hover text)

tech-stack:
  added: []
  patterns:
    - "entry_points(group='skilllint.adapters') for adapter discovery — no core modification needed for third-party adapters"
    - "@runtime_checkable Protocol for structural subtyping — isinstance without inheritance"
    - "Violation as plain dict {code, severity, message} — matches existing codebase test contracts"
    - "check_skill_md() reads and parses file itself; run_as_series() accepts pre-parsed frontmatter for pipeline use"

key-files:
  created:
    - packages/skilllint/adapters/protocol.py
    - packages/skilllint/adapters/__init__.py
    - packages/skilllint/adapters/claude_code/__init__.py
    - packages/skilllint/adapters/claude_code/adapter.py
    - packages/skilllint/adapters/cursor/__init__.py
    - packages/skilllint/adapters/cursor/adapter.py
    - packages/skilllint/adapters/codex/__init__.py
    - packages/skilllint/adapters/codex/adapter.py
    - packages/skilllint/rules/__init__.py
    - packages/skilllint/rules/as_series.py
  modified:
    - pyproject.toml

key-decisions:
  - "Protocol methods are id(), path_patterns(), applicable_rules(), validate() — NOT platform_id property + get_schema() (test contracts are ground truth over plan spec)"
  - "check_skill_md(path) is the primary AS-series entry point — test_as_series.py imports this, not run_as_series()"
  - "Stub adapters created now so test_adapters.py collects without ImportError; full validation logic deferred to 02-04"
  - "Violations returned as plain dict {code, severity, message} matching existing Violation shape in codebase"
  - "AS006 checks for eval_queries.json OR any *eval*.json/*queries*.json file — per plan spec"

patterns-established:
  - "Adapter stub pattern: implement Protocol, return empty validate(), full logic in later plan"
  - "entry_points patch target: 'skilllint.adapters.importlib.metadata.entry_points' (module-level import required)"

requirements-completed:
  - ADPT-01

duration: 18min
completed: 2026-03-09
---

# Phase 2 Plan 02: PlatformAdapter Protocol + AS-series Rules Summary

**@runtime_checkable PlatformAdapter Protocol with entry_points registry and AS001-AS006 SKILL.md rule engine using check_skill_md() returning list[dict]**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-09T20:38:03Z
- **Completed:** 2026-03-09T20:56:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- PlatformAdapter @runtime_checkable Protocol with four structural methods — any duck-typed class satisfies isinstance without inheritance
- load_adapters() discovers adapters via importlib.metadata entry_points; third-party adapters register via their own pyproject.toml without touching core
- check_skill_md() AS001-AS006 rule engine: name format, directory match, description presence/HTML, body length, eval queries presence
- Stub claude_code/cursor/codex adapter classes so test_adapters.py collects; full implementations deferred to plan 02-04

## Task Commits

1. **Task 1: PlatformAdapter Protocol + load_adapters registry** - `62788ab` (feat)
2. **Task 2: AS-series rules AS001-AS006** - `d9ab8cb` (feat)

## Files Created/Modified

- `packages/skilllint/adapters/protocol.py` - @runtime_checkable PlatformAdapter Protocol
- `packages/skilllint/adapters/__init__.py` - load_adapters() + matches_file() registry
- `packages/skilllint/adapters/claude_code/adapter.py` - ClaudeCodeAdapter stub
- `packages/skilllint/adapters/cursor/adapter.py` - CursorAdapter stub
- `packages/skilllint/adapters/codex/adapter.py` - CodexAdapter stub
- `packages/skilllint/rules/as_series.py` - check_skill_md() + AS001-AS006 + AS_RULES dict
- `packages/skilllint/rules/__init__.py` - package marker
- `pyproject.toml` - added [project.entry-points."skilllint.adapters"] section

## Decisions Made

- Protocol methods are `id()`, `path_patterns()`, `applicable_rules()`, `validate()` — the plan spec described `platform_id` property and `get_schema()` but the test stubs (ground truth from 02-01) use the four-method shape. Implemented to match tests.
- `check_skill_md(path)` is the AS-series entry point — test_as_series.py imports this name. `run_as_series()` provided as alias for plan spec compatibility.
- Stub adapter classes required immediately because test_adapters.py imports all three at module level — ImportError at collection time would prevent the four scoped Task 1 tests from running.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Stub adapter classes for test collection**
- **Found during:** Task 1 (PlatformAdapter Protocol)
- **Issue:** test_adapters.py has top-level imports of ClaudeCodeAdapter, CursorAdapter, CodexAdapter — the file would fail collection (ImportError) making it impossible to run the four Task 1 tests without these classes existing
- **Fix:** Created minimal Protocol-compliant stubs in adapters/claude_code/, adapters/cursor/, adapters/codex/ — each returns empty validate() list; full validation logic in plan 02-04
- **Files modified:** 6 new files (adapter __init__.py + adapter.py per platform)
- **Verification:** test_protocol_defined, test_runtime_checkable, test_entry_points_discovery, test_third_party_adapter_discovery — all 4 pass
- **Committed in:** 62788ab (Task 1 commit)

**2. [Rule 1 - Bug] Plan spec/test contract mismatch — Protocol method names**
- **Found during:** Task 1 discovery (reading test stubs from 02-01)
- **Issue:** Plan <action> specifies `platform_id` property + `get_schema(file_type)` but test_adapters.py uses `id()`, `path_patterns()`, `applicable_rules()`, `validate()` — plan spec and test contracts disagree
- **Fix:** Implemented Protocol to match test contracts (tests are the authoritative source of truth; spec is advisory)
- **Files modified:** packages/skilllint/adapters/protocol.py
- **Verification:** test_runtime_checkable passes — isinstance(MockAdapter(), PlatformAdapter) returns True
- **Committed in:** 62788ab (Task 1 commit)

**3. [Rule 1 - Bug] Plan spec/test contract mismatch — AS-series entry point name**
- **Found during:** Task 2 discovery (reading test stubs from 02-01)
- **Issue:** Plan specifies `run_as_series(path, frontmatter, body_lines)` but test_as_series.py imports `check_skill_md(path)` — different function name and signature
- **Fix:** Implemented `check_skill_md(path)` as primary entry point (reads file, parses frontmatter, runs all rules). Added `run_as_series()` as alias for plan spec compatibility.
- **Files modified:** packages/skilllint/rules/as_series.py
- **Verification:** All 7 AS-series tests pass
- **Committed in:** d9ab8cb (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 spec/test contract mismatches)
**Impact on plan:** All fixes necessary for tests to pass and collection to succeed. No scope creep. Stub adapters will be replaced by full implementations in plan 02-04.

## Issues Encountered

None beyond the plan spec/test contract mismatches documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PlatformAdapter Protocol established — plan 02-04 adapters implement this contract
- AS-series rules ready — plan 02-03 validation pipeline can call check_skill_md()
- Entry points registered in pyproject.toml — third-party adapters can extend without core changes
- Pre-existing 529 tests still passing (71% coverage with full suite)

---
*Phase: 02-platform-adapters*
*Completed: 2026-03-09*
