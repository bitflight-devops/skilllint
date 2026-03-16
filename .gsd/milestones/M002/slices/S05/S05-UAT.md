---
id: S05-UAT
parent: M002
milestone: M002
slice: S05
status: complete
verification_type: artifact-driven
---

# S05-UAT — Maintainer Extension Guide Verification

**Milestone:** M002
**Slice:** S05 (Maintainer extension-path documentation)
**Verification Type:** Artifact-driven (documentation task)
**Completed:** 2026-03-16

## Why Artifact-Driven

This slice delivers documentation (a file), not runtime behavior. Verification is performed by inspecting the artifact for required content patterns and confirming referenced files exist.

## Preconditions

- None required — just need file system access to the repository

## Smoke Test

```bash
# Verify guide exists
test -f docs/maintainer-extension-guide.md && echo "PASS: Guide exists" || echo "FAIL: Guide missing"
```

## Test Cases

### Test Case 1: Guide Exists and Has Substantial Content

**Steps:**
1. `test -f docs/maintainer-extension-guide.md`
2. `wc -l docs/maintainer-extension-guide.md`

**Expected:** File exists with >100 lines (actual: 312 lines)

---

### Test Case 2: ValidatorOwnership Referenced

**Steps:**
```bash
grep -c "ValidatorOwnership" docs/maintainer-extension-guide.md
```

**Expected:** ≥1 (actual: 15)

---

### Test Case 3: PlatformAdapter Referenced

**Steps:**
```bash
grep -c "PlatformAdapter" docs/maintainer-extension-guide.md
```

**Expected:** ≥1 (actual: 6)

---

### Test Case 4: ScanDiscoveryMode Referenced

**Steps:**
```bash
grep -c "ScanDiscoveryMode\|detect_discovery_mode" docs/maintainer-extension-guide.md
```

**Expected:** ≥1 (actual: 3)

---

### Test Case 5: Authority (Provenance) Referenced

**Steps:**
```bash
grep -c "authority" docs/maintainer-extension-guide.md
```

**Expected:** ≥1 (actual: 11)

---

### Test Case 6: All Referenced File Paths Exist

**Steps:** Verify each path from Quick Reference table exists:
- `packages/skilllint/schemas/claude_code/v1.json`
- `packages/skilllint/adapters/protocol.py`
- `packages/skilllint/adapters/registry.py`
- `packages/skilllint/rules/as_series.py`
- `packages/skilllint/plugin_validator.py`
- `packages/skilllint/scan_runtime.py`
- `packages/skilllint/rule_registry.py`

**Expected:** All paths exist (verified manually)

---

### Test Case 7: Decision Tree Present at Guide Top

**Steps:**
```bash
grep -A5 "Where Does This Belong" docs/maintainer-extension-guide.md
```

**Expected:** Table or decision tree found near the top of the file

---

### Test Case 8: Four Extension Path Sections Present

**Steps:**
```bash
grep -c "^## Section" docs/maintainer-extension-guide.md
```

**Expected:** Returns 4 (four distinct sections covering each extension path)

---

## Edge Cases

### File Path Staleness After Future Refactors

If file paths in the guide become stale after future refactors, maintainers should update the Quick Reference table and section examples. The guide uses real paths as of March 2026.

## Failure Signals

- Guide file missing → `test -f` fails
- No ValidatorOwnership references → grep returns 0
- Referenced file paths missing → ls on path fails

## Requirements Proved By This UAT

| Requirement | What This UAT Proves |
|-------------|---------------------|
| R020 — Document how to add a schema update | Section 1 exists with concrete schema update example |
| R021 — Document how to add a provider overlay | Section 2 exists with concrete provider adapter example |
| R022 — Document how to add a new lint rule | Section 3 exists with concrete lint rule example |
| R023 — Document how to add provenance metadata | Section 4 exists with concrete provenance metadata example |

## Not Proven By This UAT

- Runtime behavior of any extension paths (not applicable — this is documentation)
- External repo scanning (S06 responsibility)
- CLI correctness (S06 responsibility)

## Notes for Tester

- This UAT is artifact-driven, not runtime-driven
- All verification is performed via grep and file existence checks
- The guide is designed as a single reference — future maintainers should not need to read multiple files to understand extension patterns
- All file paths mentioned are real and verified to exist in the repo as of this slice
