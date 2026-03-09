---
phase: 02-platform-adapters
plan: 01
subsystem: testing
tags: [pytest, tdd, fixtures, adapters, as-series, claude-code, cursor, codex]

# Dependency graph
requires:
  - phase: 01-package-structure
    provides: skilllint package structure, importlib.resources schema pattern, conftest.py fixture patterns
provides:
  - Failing test stubs for ADPT-01 through ADPT-05 (PlatformAdapter Protocol, entry_points discovery, per-platform validation)
  - Failing test stubs for AS001–AS006 agentskills.io rule checks
  - Fixture files for claude_code, cursor, and codex platforms (valid and invalid examples)
affects:
  - 02-02-platform-adapter-protocol
  - 02-03-claude-code-adapter
  - 02-04-cursor-adapter
  - 02-05-codex-adapter

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD Wave 0: test files import non-existent modules — entire file fails RED at collection time"
    - "Fixture directory layout: tests/fixtures/{platform}/ with valid_* and invalid_* files"
    - "check_skill_md(path) as the AS-series rule entry point signature"
    - "Violation dict shape: {code, severity, message} — established by test assertions"

key-files:
  created:
    - packages/skilllint/tests/test_adapters.py
    - packages/skilllint/tests/test_as_series.py
    - packages/skilllint/tests/fixtures/claude_code/valid_plugin.json
    - packages/skilllint/tests/fixtures/claude_code/invalid_plugin.json
    - packages/skilllint/tests/fixtures/claude_code/valid_skill.md
    - packages/skilllint/tests/fixtures/claude_code/invalid_skill.md
    - packages/skilllint/tests/fixtures/cursor/valid_rule.mdc
    - packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc
    - packages/skilllint/tests/fixtures/cursor/valid_skill.md
    - packages/skilllint/tests/fixtures/codex/valid_agents.md
    - packages/skilllint/tests/fixtures/codex/empty_agents.md
    - packages/skilllint/tests/fixtures/codex/valid_rules.rules
    - packages/skilllint/tests/fixtures/codex/invalid_rules.rules
    - packages/skilllint/tests/fixtures/codex/valid_skill.md
  modified: []

key-decisions:
  - "Violation dict shape {code, severity, message} locked by test assertions — implementations must conform"
  - "check_skill_md(path: pathlib.Path) -> list[dict] is the AS-series entry point — tests call it directly"
  - "Adapter interface: id(), path_patterns(), applicable_rules(), validate(path) — established by test stubs"
  - "AS005 severity must be 'warning' or 'warn'; AS006 severity must be 'info' or 'information' — locked by test assertions"

patterns-established:
  - "Wave 0 TDD: whole-file ImportError on collection is correct RED state — do not add try/except guards"
  - "Fixture files are realistic — valid fixtures pass zero violations, invalid fixtures produce at least one"
  - "Test names match VALIDATION.md task IDs for traceability (e.g. test_as001_name_format_valid)"

requirements-completed:
  - ADPT-01
  - ADPT-02
  - ADPT-03
  - ADPT-04
  - ADPT-05

# Metrics
duration: 5min
completed: 2026-03-09
---

# Phase 2 Plan 01: Wave 0 TDD Scaffold Summary

**pytest failing stubs for ADPT-01–ADPT-05 and AS001–AS006 with realistic claude_code/cursor/codex fixture files — all RED via ModuleNotFoundError**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-09T20:33:41Z
- **Completed:** 2026-03-09T20:38:45Z
- **Tasks:** 1 (single wave 0 scaffold task)
- **Files modified:** 14

## Accomplishments

- test_adapters.py: 10 test stubs covering PlatformAdapter Protocol, entry_points discovery, ClaudeCodeAdapter/CursorAdapter/CodexAdapter path patterns and validation
- test_as_series.py: 7 test stubs covering AS001–AS006 rule checks with tmp_path fixtures
- 14 fixture files across claude_code/, cursor/, codex/ directories — realistic valid and invalid examples for each platform
- RED state confirmed: both files fail collection with ModuleNotFoundError for `skilllint.adapters` and `skilllint.rules`

## Task Commits

1. **Wave 0 scaffold: test stubs and fixtures** - `cafdc0d` (test)

**Plan metadata:** (created below)

## Files Created/Modified

- `packages/skilllint/tests/test_adapters.py` - 10 stubs for ADPT-01 through ADPT-05
- `packages/skilllint/tests/test_as_series.py` - 7 stubs for AS001–AS006
- `packages/skilllint/tests/fixtures/claude_code/valid_plugin.json` - minimal valid plugin.json (name, description, version, schema_version)
- `packages/skilllint/tests/fixtures/claude_code/invalid_plugin.json` - missing required name field
- `packages/skilllint/tests/fixtures/claude_code/valid_skill.md` - valid agentskills.io SKILL.md frontmatter
- `packages/skilllint/tests/fixtures/claude_code/invalid_skill.md` - name "My_Skill!" triggers AS001
- `packages/skilllint/tests/fixtures/cursor/valid_rule.mdc` - description, globs, alwaysApply frontmatter
- `packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc` - unknown_field only, missing description
- `packages/skilllint/tests/fixtures/cursor/valid_skill.md` - valid SKILL.md for cursor
- `packages/skilllint/tests/fixtures/codex/valid_agents.md` - non-empty AGENTS.md
- `packages/skilllint/tests/fixtures/codex/empty_agents.md` - completely empty file
- `packages/skilllint/tests/fixtures/codex/valid_rules.rules` - prefix_rule() with pattern, decision, justification
- `packages/skilllint/tests/fixtures/codex/invalid_rules.rules` - prefix_rule() with unknown field "owner"
- `packages/skilllint/tests/fixtures/codex/valid_skill.md` - valid SKILL.md for codex

## Decisions Made

- Violation dict shape `{code, severity, message}` locked by test assertions — plan 02-02 implementations must conform to this interface
- `check_skill_md(path: pathlib.Path) -> list[dict]` established as the AS-series entry point
- Adapter interface locked: `id()`, `path_patterns()`, `applicable_rules()`, `validate(path)` — test stubs call these directly
- AS005 severity must be `"warning"` or `"warn"`; AS006 must be `"info"` or `"information"` — enforced by test assertions

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Wave 0 complete: all VALIDATION.md Wave 0 requirements satisfied
- Plans 02-02 through 02-05 can proceed — each turns tests GREEN as modules land
- Fixture files are the ground truth for adapter validation behavior — do not modify without updating corresponding tests

## Self-Check

- [x] `packages/skilllint/tests/test_adapters.py` — exists
- [x] `packages/skilllint/tests/test_as_series.py` — exists
- [x] `packages/skilllint/tests/fixtures/claude_code/valid_plugin.json` — exists
- [x] `packages/skilllint/tests/fixtures/cursor/valid_rule.mdc` — exists
- [x] `packages/skilllint/tests/fixtures/codex/valid_rules.rules` — exists
- [x] Commit `cafdc0d` — confirmed

## Self-Check: PASSED

---
*Phase: 02-platform-adapters*
*Completed: 2026-03-09*
