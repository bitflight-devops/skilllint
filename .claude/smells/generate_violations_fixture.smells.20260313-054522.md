# Code Smell Report: generate_violations_fixture.py

**File**: `/home/user/agentskills-linter/scripts/generate_violations_fixture.py`
**Date**: 2026-03-13T05:45:22Z

## Issues Found

### LOW: SKILL_BODY template re-formatted on every iteration (line 237)

`build_skill_md()` calls `SKILL_BODY.format(title=title, violation=violation.value)`
inside the loop (called from line 310). The body template is ~1KB and `.format()` is
fast, but the body content is identical except for `title` and `violation` which are
cheap substitutions. No real issue here.

### LOW: ViolationSummary uses dict.get instead of Counter (line 289)

`self.counts.get(violation, 0) + 1` reimplements `collections.Counter` behavior.

- **Line**: 289
- **Fix**: Use `collections.Counter[ViolationType]` for `counts` field.

No significant efficiency issues found in this file. The zip generation is
well-structured with a single-pass write.
