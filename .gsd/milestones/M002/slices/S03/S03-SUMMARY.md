---
id: S03
parent: M002
milestone: M002
provides:
  - ScanDiscoveryMode enum (MANIFEST, AUTO, STRUCTURE)
  - PluginManifest dataclass
  - detect_discovery_mode() function
  - read_plugin_manifest() function
  - get_manifest_discovery_paths() function
  - get_structure_discovery_paths() function
  - test_discovery_modes.py with 16 tests
  - Updated resolve_filter_and_expand_paths() with three-mode discovery
requires:
  - slice: S01
    provides: scan_runtime.py seams
  - slice: S02
    provides: ValidatorOwnership model
affects:
  - M002/S04 (builds on correct scan target selection)
  - M002/S05 (docs will describe discovery modes)
key_files:
  - packages/skilllint/scan_runtime.py (discovery mode additions)
  - packages/skilllint/tests/test_discovery_modes.py
key_decisions:
  - Used enum for discovery modes for clarity
  - Provider directory detection includes nested paths
  - Manifest discovery only includes explicitly declared files
patterns_established:
  - Three distinct discovery modes with explicit selection
  - Discovery mode is observable via detect_discovery_mode()
  - Tests lock discovery behavior as contract
observability_surfaces:
  - detect_discovery_mode() returns mode for logging
  - Test output shows which mode is selected
drill_down_paths:
  - .gsd/milestones/M002/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T03-SUMMARY.md
duration: 40m (T01:15m + T02:15m + T03:10m)
verification_result: passed
completed_at: 2026-03-15
---

# S03: Scan Target Discovery Contract

**Implemented three-mode scan target discovery (manifest, auto, structure) with 16 passing tests.**

## What Happened

Slice S03 established explicit contracts for how scan targets are selected based on discovery mode (R015, R016, R017).

### Task Execution

**T01: Add plugin.json component detection** ✓
- Created `PluginManifest` dataclass
- Created `read_plugin_manifest()` function
- Created `detect_discovery_mode()` function

**T02: Implement three-mode discovery** ✓
- Created `ScanDiscoveryMode` enum
- Created `get_manifest_discovery_paths()` for explicit component extraction
- Created `get_structure_discovery_paths()` for provider directory scanning
- Updated `resolve_filter_and_expand_paths()` to use discovery modes

**T03: Add discovery contract tests** ✓
- Created `test_discovery_modes.py` with 16 tests
- All discovery modes covered with tests

## Verification

```
$ uv run pytest packages/skilllint/tests/test_discovery_modes.py -v --no-cov
16 passed in 1.80s

$ uv run pytest packages/skilllint/tests/test_cli.py -q --no-cov
35 passed, 1 skipped

$ uv run python -m skilllint.plugin_validator check packages/skilllint/tests/fixtures/claude_code/valid_skill.md --no-color
Exit: 0
```

## Requirements Advanced

- R015 — Use manifest-driven scanning — **advanced** (MANIFEST mode implemented)
- R016 — Use documented auto-discovery — **advanced** (AUTO mode implemented)
- R017 — Use structure-based discovery — **advanced** (STRUCTURE mode implemented)

## Requirements Validated

None yet.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

1. **S04: Official-repo hard-failure truth pass** — Use discovery modes for correct target selection

## Files Created/Modified

- `packages/skilllint/scan_runtime.py` — Added ScanDiscoveryMode, PluginManifest, detection functions
- `packages/skilllint/tests/test_discovery_modes.py` — New test module with 16 discovery tests