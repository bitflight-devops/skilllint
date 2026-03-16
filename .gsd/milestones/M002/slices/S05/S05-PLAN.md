# S05: Maintainer extension-path documentation

**Goal:** Maintainers have a single reference showing how to add a schema update, provider overlay, lint rule, and provenance metadata in the post-refactor architecture.
**Demo:** `docs/maintainer-extension-guide.md` exists with four worked examples that reference real files and reflect the ownership model from S02, discovery model from S03, and severity classification from S04.

## Must-Haves

- Worked example: adding a versioned schema to `packages/skilllint/schemas/<provider>/`
- Worked example: implementing a new `PlatformAdapter` and registering it in `packages/skilllint/adapters/`
- Worked example: adding a new lint rule in `packages/skilllint/rules/` with correct `ValidatorOwnership` and `VALIDATOR_OWNERSHIP` registration
- Worked example: attaching provenance/authority metadata to schemas and rules
- All examples reference post-refactor architecture (ownership model, discovery modes, severity classification) — not the legacy monolith

## Verification

- `test -f docs/maintainer-extension-guide.md` — file exists
- `grep -c "ValidatorOwnership" docs/maintainer-extension-guide.md` returns ≥1 — ownership model referenced
- `grep -c "ScanDiscoveryMode\|detect_discovery_mode" docs/maintainer-extension-guide.md` returns ≥1 — discovery model referenced
- `grep -c "PlatformAdapter" docs/maintainer-extension-guide.md` returns ≥1 — adapter protocol referenced
- `grep -c "authority" docs/maintainer-extension-guide.md` returns ≥1 — provenance metadata covered
- All file paths mentioned in the guide exist in the repo (manual spot-check by executor)

## Tasks

- [x] **T01: Write maintainer extension guide with four worked examples** `est:45m`
  - Why: Delivers R020, R021, R022, R023 — the four documentation requirements this slice owns
  - Files: `docs/maintainer-extension-guide.md`
  - Do: Create guide with four sections (schema update, provider overlay, lint rule, provenance metadata). Each section must include: (1) which directory/files to touch, (2) a concrete code snippet showing the pattern, (3) how to register/wire the new component, (4) how to verify it works. Reference real existing files as templates. Cross-reference the ownership model (`ValidatorOwnership` in `plugin_validator.py`), discovery modes (`ScanDiscoveryMode` in `scan_runtime.py`), and severity classification from S04. Include a "Where does this belong?" decision tree at the top.
  - Verify: Run the five grep checks from the Verification section above. Spot-check that all referenced file paths exist.
  - Done when: Guide covers all four extension paths with concrete examples that reference the real post-refactor architecture.

## Files Likely Touched

- `docs/maintainer-extension-guide.md` (new)
