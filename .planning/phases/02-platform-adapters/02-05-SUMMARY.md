---
phase: 02-platform-adapters
plan: 05
status: complete
completed: "2026-03-10"
---

# Plan 02-05 Summary: --platform CLI flag + adapter dispatch

## What Was Built

- `--platform` flag wired into Typer CLI in `plugin_validator.py` (initial bundled adapters: claude-code, cursor, codex; see `.claude/vendor/CLAUDE.md` for all supported platforms)
- `validate_file()` dispatch function routing to adapters based on platform override or auto-detection
- `run_platform_checks()` dispatching to CursorAdapter, CodexAdapter, ClaudeCodeAdapter
- `is_skill_md()` and `parse_skill_md()` helpers
- AS-series structural deduplication: fires once per file before per-adapter loop

## Verification Results

**Test suite:** 555 passed, 1 skipped — all GREEN

**End-to-end spot checks:**
| Command | Expected | Result |
|---------|----------|--------|
| `skilllint --platform cursor valid_rule.mdc` | exit 0 | ✅ |
| `skilllint --platform cursor invalid_rule.mdc` | exit 1, mentions "description" | ✅ |
| `skilllint --platform codex empty_agents.md` | exit 1, mentions "empty" | ✅ |
| `skilllint --platform codex valid_rules.rules` | exit 0 | ✅ |
| Adapter IDs: `[x.id() for x in load_adapters()]` | all three IDs | ✅ `['claude_code', 'codex', 'cursor']` |

## Implementation Notes

- `load_adapters()` returns `list[PlatformAdapter]` (not `dict`) — the plan's checkpoint command #6 used `.keys()` which reflects the plan's interface pattern, but the implementation uses a list; plan artifact issue only, CLI behavior is correct
- All 8 platform CLI tests were pre-written (from commit `adef08d`) and passed green — task was already implemented

## Phase 2 Complete

All 5 plans in Phase 2 (platform-adapters) are done:
- 02-01: PlatformAdapter Protocol + AS001–AS006 rules
- 02-02: AS-series rule implementations + adapter stubs
- 02-03: Cursor and Codex schema packages
- 02-04: Three bundled adapters (ClaudeCode, Cursor, Codex)
- 02-05: CLI --platform flag + adapter dispatch
