---
task: "14"
title: "Report Counting Fix"
status: completed
agent: "@python-cli-architect"
priority: 3
complexity: s
---

## Task 14: Report Counting Fix

**Status**: ALREADY IMPLEMENTED (imported from claude_skills)
**Agent**: @python-cli-architect
**Priority**: 3
**Complexity**: S

#### Context

ConsoleReporter was counting validators instead of files in its summary output. The fix uses
`total_files` (number of unique files validated) rather than validator count.

#### Implementation (Already Complete)

The fix is fully implemented in `packages/skilllint/plugin_validator.py`:

- **`_compute_summary`** (line ~5306): Returns `(total_files, passed, failed, warnings)` where
  `total_files = len(all_results)` — counts unique file paths, not validator instances.

- **`ConsoleReporter.summarize`** (line ~4700): Signature is
  `summarize(self, total_files: int, passed: int, failed: int, warnings: int)` and displays
  `Total files: {total_files}` in the summary panel.

- **Call site in `main()`**: `reporter.summarize(*_compute_summary(all_results))` — the tuple
  is unpacked directly, ensuring file-level counts flow through correctly.

#### Verification

```bash
cd .worktrees/initial-packaging
# Run against a real plugin directory and check "Total files:" in output
uv run skilllint ~/.claude/plugins/cache/jamie-bitflight-skills/plugin-creator/5.12.2/
```

No action required — this task is complete.
