---
id: S03
parent: M002
milestone: M002
title: Scan target discovery contract
status: in_progress
depends: [S01]
risk: high
reviewers: []
---

# S03: Scan Target Discovery Contract

## Scope

This slice establishes explicit contracts for how scan targets are selected based on the three discovery modes:
- R015: Manifest-driven scanning (plugin.json explicitly enumerates components)
- R016: Auto-discovery (plugin.json exists but omits component arrays)
- R017: Structure-based discovery (provider directories like .claude/ without manifests)

## What We Learned from S01/S02

- `scan_runtime.py` provides `discover_validatable_paths()` and `resolve_filter_and_expand_paths()`
- `ValidatorOwnership` model in place for R013/R014
- Current code checks for `.claude-plugin/plugin.json` but doesn't distinguish between manifest types

## What S03 Must Solve

Current behavior in `resolve_filter_and_expand_paths()`:
```python
if (path / ".claude-plugin/plugin.json").exists():
    expanded_paths.append(path)
    # Also validate SKILL.md files
    expanded_paths.extend(sorted(path.glob("**/skills/*/SKILL.md")))
else:
    expanded_paths.extend(discover_validatable_paths(path))
```

This treats all plugin.json directories the same. The gap is:
- Doesn't check if plugin.json has explicit `agents`, `commands`, `skills`, or `hooks` arrays
- Doesn't handle provider directories (`.claude/`, `.agent/`, `.agents/`, `.gemini/`, `.cursor/`) separately

## Key Insight

The scan target contract should be:
1. **Manifest-driven**: Read plugin.json → if it has explicit arrays → scan only those
2. **Auto-discovery**: Read plugin.json → if no explicit arrays → use DEFAULT_SCAN_PATTERNS  
3. **Structure-based**: No plugin.json → detect provider directory type → use appropriate patterns

## Execution Plan

1. **T01: Add plugin.json component detection** — Detect whether manifest has explicit component arrays
2. **T02: Implement three-mode discovery** — Create explicit discovery mode selection in scan_runtime
3. **T03: Add discovery contract tests** — Lock discovery behavior with tests

## Success Criteria

After S03:
- Scan mode is logged/observable for each scan
- Manifest-driven mode only scans explicitly declared components
- Auto-discovery mode uses documented patterns
- Structure-based mode handles provider directories correctly
