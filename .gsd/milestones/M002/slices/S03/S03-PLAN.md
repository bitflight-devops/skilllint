# S03 Plan: Scan Target Discovery Contract

**Parent:** M002
**Status:** in_progress
**Risk:** high

## Tasks

- [x] **T01: Add plugin.json component detection** `est:30m`
  > Detect whether plugin.json has explicit component arrays (agents, commands, skills, hooks). Create function to read manifest and return component lists or None.

- [x] **T02: Implement three-mode discovery** `est:45m`
  > Update scan_runtime.py to select discovery mode:
  > - Manifest-driven: use explicit arrays from plugin.json
  > - Auto-discovery: use DEFAULT_SCAN_PATTERNS
  > - Structure-based: detect provider directory type and use appropriate patterns

- [x] **T03: Add discovery contract tests** `est:30m`
  > Lock discovery behavior with tests verifying each mode selects correct files.

## Dependencies

- S01 (completed) — provides scan_runtime.py seams
- S02 (completed) — provides ValidatorOwnership model

## Notes

- Current code treats all plugin.json directories the same
- Need to detect provider directories (.claude/, .agent/, .agents/, .gemini/, .cursor/)
- Discovery mode should be logged for observability

## Verification

- Tests pass for all three discovery modes
- Manifest-driven scans only declared components
- Auto-discovery uses documented patterns
- Structure-based handles provider directories correctly
