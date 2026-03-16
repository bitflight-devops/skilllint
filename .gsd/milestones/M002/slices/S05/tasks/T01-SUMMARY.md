---
id: T01
parent: S05
milestone: M002
provides:
  - Maintainer extension guide with four worked examples
key_files:
  - docs/maintainer-extension-guide.md
key_decisions:
  - Used real file references (not invented paths) throughout guide
  - Included both protocol-based and entry-point-based adapter registration patterns
patterns_established:
  - Decision tree at guide top for extension path selection
  - Authority dict structure for provenance metadata
  - VALIDATOR_OWNERSHIP / VALIDATOR_CONSTRAINT_SCOPES registration pattern
observability_surfaces:
  - None (documentation task)
duration: 20m
verification_result: passed
completed_at: 2026-03-16T00:15:00-04:00
blocker_discovered: false
---

# T01: Write maintainer extension guide with four worked examples

**Created comprehensive maintainer extension guide with four worked examples referencing real post-refactor architecture.**

## What Happened

Read the five input files referenced in the task plan to ensure accurate references:
- `packages/skilllint/schemas/claude_code/v1.json` — schema template with provenance structure
- `packages/skilllint/adapters/protocol.py` — PlatformAdapter protocol definition
- `packages/skilllint/adapters/registry.py` — adapter loading via entry_points
- `packages/skilllint/rules/as_series.py` — lint rule template with @skilllint_rule decorator
- `packages/skilllint/plugin_validator.py` — ValidatorOwnership enum, VALIDATOR_OWNERSHIP dict
- `packages/skilllint/scan_runtime.py` — ScanDiscoveryMode enum, detect_discovery_mode()
- `packages/skilllint/rule_registry.py` — RuleAuthority dataclass, @skilllint_rule decorator

Created `docs/maintainer-extension-guide.md` with:
1. **Decision tree** — "Where does this belong?" table and quick decision tree
2. **Section 1: Schema Update** — schema location, field structure, constraint_scope, provenance
3. **Section 2: Provider Overlay** — PlatformAdapter protocol, entry-point registration, structure-based discovery
4. **Section 3: Lint Rule** — @skilllint_rule decorator, VALIDATOR_OWNERSHIP registration, severity guidance
5. **Section 4: Provenance Metadata** — authority dict structure, schema provenance, rule authority
6. **Quick Reference table** — one-line lookup for all key patterns

## Verification

All five grep checks passed:
- `test -f docs/maintainer-extension-guide.md` — ✓ PASS
- `grep -c "ValidatorOwnership"` — 15 occurrences
- `grep -c "PlatformAdapter"` — 6 occurrences
- `grep -c "ScanDiscoveryMode\|detect_discovery_mode"` — 3 occurrences
- `grep -c "authority"` — 11 occurrences

All 8 referenced file paths verified to exist in repo.

## Diagnostics

None — this is a documentation task with no runtime behavior.

## Deviations

None — followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `docs/maintainer-extension-guide.md` — New file (13KB) with four worked examples for extending skilllint
