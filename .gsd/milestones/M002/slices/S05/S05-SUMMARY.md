---
id: S05
parent: M002
milestone: M002
provides:
  - Maintainer extension guide with four worked examples covering schema updates, provider overlays, lint rules, and provenance metadata
requires:
  - slice: S02
    provides: Ownership model (ValidatorOwnership enum, VALIDATOR_OWNERSHIP dict)
  - slice: S03
    provides: Discovery model (ScanDiscoveryMode enum, detect_discovery_mode(), PROVIDER_DIR_NAMES)
  - slice: S04
    provides: Severity classification guidance and rule-truth evaluation
affects:
  - S06
key_files:
  - docs/maintainer-extension-guide.md
key_decisions:
  - Used real file references throughout guide (no invented paths)
  - Included both entry-point-based and protocol-based adapter registration patterns
  - Placed decision tree at guide top for quick extension path selection
patterns_established:
  - "Where does this belong?" decision tree for extension path selection
  - Authority dict structure for provenance metadata across schema and rules
  - VALIDATOR_OWNERSHIP / VALIDATOR_CONSTRAINT_SCOPES registration pattern for lint rules
  - @skilllint_rule decorator usage with authority kwarg
observability_surfaces:
  - None (documentation task with no runtime behavior)
duration: 20m
verification_result: passed
completed_at: 2026-03-16T00:15:00-04:00
---

# S05: Maintainer extension-path documentation

**Maintainer extension guide created with four worked examples referencing real post-refactor architecture.**

## What Happened

Read seven source files to ensure accurate real-file references throughout the guide:
- `packages/skilllint/schemas/claude_code/v1.json` — schema template with provenance structure
- `packages/skilllint/adapters/protocol.py` — PlatformAdapter protocol definition
- `packages/skilllint/adapters/registry.py` — adapter loading via entry_points
- `packages/skilllint/rules/as_series.py` — lint rule template with @skilllint_rule decorator
- `packages/skilllint/plugin_validator.py` — ValidatorOwnership enum, VALIDATOR_OWNERSHIP dict
- `packages/skilllint/scan_runtime.py` — ScanDiscoveryMode enum, detect_discovery_mode()
- `packages/skilllint/rule_registry.py` — RuleAuthority dataclass, @skilllint_rule decorator

Created `docs/maintainer-extension-guide.md` (13KB) with:

1. **Decision tree** at top — "Where does this belong?" table and quick decision flow for selecting extension path
2. **Section 1: Schema Update** — schema file locations, field structure with `constraint_scope`, provenance dict, hard-error behavior from ValidatorOwnership.SCHEMA
3. **Section 2: Provider Overlay** — PlatformAdapter protocol, entry-point registration, structure-based discovery via PROVIDER_DIR_NAMES
4. **Section 3: Lint Rule** — @skilllint_rule decorator, VALIDATOR_OWNERSHIP registration, severity guidance table
5. **Section 4: Provenance Metadata** — authority dict structure for both schemas and rules, RuleAuthority dataclass
6. **Quick Reference table** — one-line lookup for all key patterns and file locations

## Verification

All five grep verification checks passed:
- `test -f docs/maintainer-extension-guide.md` — ✓ PASS
- `grep -c "ValidatorOwnership"` — 15 occurrences (≥1 required)
- `grep -c "PlatformAdapter"` — 6 occurrences (≥1 required)
- `grep -c "ScanDiscoveryMode\|detect_discovery_mode"` — 3 occurrences (≥1 required)
- `grep -c "authority"` — 11 occurrences (≥1 required)

All 8 referenced file paths manually verified to exist in repo.

## Requirements Advanced

- R020 — Document how to add a schema update → **covered** in Section 1
- R021 — Document how to add a provider overlay → **covered** in Section 2
- R022 — Document how to add a new lint rule → **covered** in Section 3
- R023 — Document how to add provenance metadata → **covered** in Section 4

## Requirements Validated

No requirements moved to Validated state — S05 delivers documentation, and R020-R023 are the proof of documentation existence.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None — followed task plan exactly.

## Known Limitations

None.

## Follow-ups

None — S05 documentation is complete and doesn't require follow-up work.

## Files Created/Modified

- `docs/maintainer-extension-guide.md` — New file (13KB) with comprehensive maintainer guide including decision tree and four worked examples

## Forward Intelligence

### What the next slice should know
- The extension guide references all key architectural patterns from S01-S04 — no new patterns were introduced in S05
- All file paths in the guide are real and verified to exist
- The guide is designed to be the single reference for maintainers extending skilllint

### What's fragile
- Nothing fragile — this is documentation with no runtime behavior

### Authoritative diagnostics
- N/A — documentation task

### What assumptions changed
- None — assumed the guide could reference real files, confirmed all paths exist

---

# S05-UAT — Maintainer Extension Guide

**Milestone:** M002
**Written:** 2026-03-16

## UAT Type

- UAT mode: **artifact-driven**
- Why this mode is sufficient: This slice delivers documentation (a file), not runtime behavior. Verification is performed by inspecting the artifact for required content patterns and confirming referenced files exist.

## Preconditions

- None required — just need file system access to the repository

## Smoke Test

```bash
# Verify guide exists
test -f docs/maintainer-extension-guide.md && echo "PASS: Guide exists" || echo "FAIL: Guide missing"
```

## Test Cases

### 1. Guide exists and is non-empty

1. Check file exists: `test -f docs/maintainer-extension-guide.md`
2. Check file has content: `wc -l docs/maintainer-extension-guide.md` should return > 100 lines
3. **Expected:** File exists with substantial content (>100 lines)

### 2. Ownership model (ValidatorOwnership) referenced

1. Run: `grep -c "ValidatorOwnership" docs/maintainer-extension-guide.md`
2. **Expected:** Returns ≥1 (actual: 15)

### 3. Adapter protocol (PlatformAdapter) referenced

1. Run: `grep -c "PlatformAdapter" docs/maintainer-extension-guide.md`
2. **Expected:** Returns ≥1 (actual: 6)

### 4. Discovery model (ScanDiscoveryMode) referenced

1. Run: `grep -c "ScanDiscoveryMode\|detect_discovery_mode" docs/maintainer-extension-guide.md`
2. **Expected:** Returns ≥1 (actual: 3)

### 5. Provenance metadata (authority) referenced

1. Run: `grep -c "authority" docs/maintainer-extension-guide.md`
2. **Expected:** Returns ≥1 (actual: 11)

### 6. All referenced file paths exist

1. Check each path from the Quick Reference table exists:
   - `packages/skilllint/schemas/claude_code/v1.json`
   - `packages/skilllint/adapters/protocol.py`
   - `packages/skilllint/adapters/registry.py`
   - `packages/skilllint/rules/as_series.py`
   - `packages/skilllint/plugin_validator.py`
   - `packages/skilllint/scan_runtime.py`
   - `packages/skilllint/rule_registry.py`
2. **Expected:** All paths exist (verified manually)

### 7. Decision tree present at guide top

1. Run: `grep -A5 "Where Does This Belong" docs/maintainer-extension-guide.md`
2. **Expected:** Table or decision tree found near the top of the file

### 8. Four extension path sections present

1. Check for section headers: Schema, Provider Overlay, Lint Rule, Provenance
   - `grep -c "^## Section" docs/maintainer-extension-guide.md` should return 4
2. **Expected:** Four distinct sections covering each extension path

## Edge Cases

### File path changes in future refactors

If file paths in the guide become stale after future refactors, maintainers should update the Quick Reference table and section examples. The guide uses real paths as of March 2026.

## Failure Signals

- Guide file missing → `test -f` fails
- No ValidatorOwnership references → grep returns 0
- Referenced file paths missing → ls on path fails

## Requirements Proved By This UAT

- R020 — Document how to add a schema update
- R021 — Document how to add a provider overlay
- R022 — Document how to add a new lint rule
- R023 — Document how to add provenance metadata

All four requirements are proven by the presence of the guide with required content patterns.

## Not Proven By This UAT

- Runtime behavior of any extension paths (not applicable — this is documentation)
- External repo scanning (S06 responsibility)
- CLI correctness (S06 responsibility)

## Notes for Tester

- This UAT is artifact-driven, not runtime-driven
- All verification is performed via grep and file existence checks
- The guide is designed as a single reference — future maintainers should not need to read multiple files to understand extension patterns
