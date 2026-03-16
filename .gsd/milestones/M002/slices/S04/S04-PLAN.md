# S04: Official-repo hard-failure truth pass

**Goal:** Disputed hard failures from official-repo scans are classified with evidence, and unjustified ones no longer cause hard failures (exit code 1) — they become reviewable warnings instead.
**Demo:** `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color` exits 0 (or exits 1 only for genuinely justified schema violations), and previously-hard-failing rules like FM004, FM007 are surfaced as warnings rather than errors.

## Must-Haves

- Every hard-failure rule family found in official repos (FM003, FM004, FM005, FM007, AS004) is classified as justified, legacy, recommendation-only, or hallucinated with documented evidence.
- Unjustified hard failures are downgraded to warnings so they no longer cause exit code 1.
- Justified hard failures remain as errors.
- A test file locks the classification decisions and verifies severity routing.
- Real CLI scans against official repos confirm exit code behavior changes.

## Proof Level

- This slice proves: integration (real CLI scans against external repos)
- Real runtime required: yes
- Human/UAT required: yes (human reviews remaining findings report)

## Verification

- `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov` — all classification tests pass
- `uv run pytest packages/skilllint/tests/ -q --no-cov` — no regressions in existing tests
- `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color` — exit code and error count reflect classification changes

## Observability / Diagnostics

- Runtime signals: rule severity in ValidationIssue objects; exit code reflects only SCHEMA-ownership errors
- Inspection surfaces: CLI output distinguishes ERROR vs WARN per finding
- Failure visibility: exit code 1 only when genuine schema errors remain
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `ValidatorOwnership` enum and `VALIDATOR_OWNERSHIP` mapping from S02; scan discovery from S03
- New wiring introduced in this slice: severity downgrades for specific rule codes in `plugin_validator.py`
- What remains before the milestone is truly usable end-to-end: S05 docs, S06 full external scan proof

## Tasks

- [x] **T01: Classify hard-failure rules and downgrade unjustified ones** `est:45m`
  - Why: The core deliverable — evidence-based classification of each disputed rule, and code changes to downgrade unjustified hard failures to warnings.
  - Files: `packages/skilllint/plugin_validator.py`, `packages/skilllint/tests/test_rule_truth.py`
  - Do: (1) Create a rule truth classification table as a code comment or docstring documenting evidence for each rule: FM003 (justified — files truly lack frontmatter), FM004 (unjustified — multiline YAML is valid YAML, Claude Code accepts it), FM005 (case-by-case — check instances), FM007 (unjustified — YAML arrays are valid, Claude Code runtime accepts both forms), AS004 (unjustified — unquoted colons are valid YAML when not ambiguous). (2) Change severity from "error" to "warning" for FM004, FM007, and AS004 findings. (3) Create `test_rule_truth.py` with tests that verify: FM003 stays error, FM004 becomes warning, FM007 becomes warning, AS004 becomes warning. (4) Verify existing tests still pass.
  - Verify: `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov && uv run pytest packages/skilllint/tests/ -q --no-cov`
  - Done when: Classification is documented in code, severity changes are wired, new tests pass, existing tests pass.

- [x] **T02: Verify official-repo scan behavior and produce findings report** `est:20m`
  - Why: Proves the classification works against real official repos and documents remaining findings for human review.
  - Files: `packages/skilllint/tests/test_rule_truth.py` (extend), `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md`
  - Do: (1) Run `skilllint check` against all three official repos and capture output. (2) Verify exit codes changed as expected (FM004/FM007/AS004 no longer cause exit 1). (3) Write a findings report documenting: remaining hard failures (justified), downgraded warnings (with evidence), and any unexpected results. (4) Add an integration test to `test_rule_truth.py` that runs the CLI against the test fixtures and verifies severity classification.
  - Verify: `uv run python -m skilllint.plugin_validator check /home/ubuntulinuxqa2/repos/claude-plugins-official --no-color; echo "exit: $?"` — exit code reflects only justified errors
  - Done when: Findings report exists, exit codes match classification, integration test passes.

## Files Likely Touched

- `packages/skilllint/plugin_validator.py`
- `packages/skilllint/tests/test_rule_truth.py`
- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md`
