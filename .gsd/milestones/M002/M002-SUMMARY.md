---
id: M002
provides:
  - explicit validator seams for scan orchestration and summary computation
  - ownership routing between schema validation and lint-rule validation
  - three-mode scan target discovery for manifest, auto-discovery, and structure-only roots
  - evidence-backed severity classification for disputed frontmatter rules
  - maintainer extension documentation with worked examples
  - external CLI regression proof and findings reports against official repos
key_decisions:
  - Keep manifest-driven, auto-discovery, and structure-only scanning as separate explicit discovery modes
  - Downgrade FM004, FM007, and AS004 to warnings because runtime behavior accepts them
  - Keep FM003 and FM005 as hard errors because they are genuine schema violations
patterns_established:
  - extract runtime seams into dedicated modules and prove wiring with import-identity tests
  - register validator ownership and constraint scopes explicitly rather than inferring them implicitly
  - classify disputed rules with evidence before treating external repos as wrong
  - prove milestone behavior through the real CLI path against external repos, not fixtures alone
observability_surfaces:
  - packages/skilllint/tests/test_scan_runtime.py
  - packages/skilllint/tests/test_ownership_routing.py
  - packages/skilllint/tests/test_discovery_modes.py
  - packages/skilllint/tests/test_rule_truth.py
  - packages/skilllint/tests/test_external_scan_proof.py
  - scripts/verify-s06.sh
  - .gsd/milestones/M002/slices/S04/S04-FINDINGS.md
  - .gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md
requirement_outcomes:
  - id: R012
    from_status: active
    to_status: validated
    proof: S01 extracted scan_runtime.py seams and locked them with 24 passing seam-boundary tests.
  - id: R013
    from_status: active
    to_status: validated
    proof: S02 added explicit ValidatorOwnership routing and S04/S06 proved schema errors and lint warnings are separated in real CLI output and exit codes.
  - id: R014
    from_status: active
    to_status: validated
    proof: S02 added explicit ownership and constraint-scope mappings; S05 documented how shared versus provider-specific behavior is extended.
  - id: R015
    from_status: active
    to_status: validated
    proof: S03 implemented manifest-mode discovery and locked it with discovery-contract tests; S06 exercised real external scans through the CLI.
  - id: R016
    from_status: active
    to_status: validated
    proof: S03 implemented documented auto-discovery mode and covered it with 16 discovery tests.
  - id: R017
    from_status: active
    to_status: validated
    proof: S03 implemented structure-based discovery for provider roots and proved it with discovery-mode regression tests.
  - id: R018
    from_status: active
    to_status: validated
    proof: S04 downgraded unjustified hard failures to warnings and S06 confirmed only genuine FM003/FM005 violations remain as hard failures in official repos.
  - id: R019
    from_status: active
    to_status: validated
    proof: S04 classified disputed rules with documented evidence and S06 findings reports preserved remaining hard failures for human review.
  - id: R020
    from_status: active
    to_status: validated
    proof: S05 created docs/maintainer-extension-guide.md with a concrete schema-update example.
  - id: R021
    from_status: active
    to_status: validated
    proof: S05 created docs/maintainer-extension-guide.md with a concrete provider-overlay example.
  - id: R022
    from_status: active
    to_status: validated
    proof: S05 created docs/maintainer-extension-guide.md with a concrete lint-rule example tied to ValidatorOwnership registration.
  - id: R023
    from_status: active
    to_status: validated
    proof: S05 created docs/maintainer-extension-guide.md with concrete provenance metadata guidance for schemas and rules.
  - id: R024
    from_status: active
    to_status: validated
    proof: S06 ran real uv-based CLI scans against ../claude-plugins-official, ../skills, and ../claude-code-plugins and verified expected exit codes.
  - id: R025
    from_status: active
    to_status: validated
    proof: S01-S03 refactors remained wired into the real CLI path, and S06 regression tests plus verify-s06.sh proved user-facing behavior stayed stable.
duration: 2026-03-15 to 2026-03-16
verification_result: passed
completed_at: 2026-03-16
---

# M002: Validator Decomposition and Scan-Truth Hardening

**`skilllint` now routes scanning and constraint evaluation through explicit seams, discovers targets correctly across three scan modes, and reports only evidence-backed hard failures when scanning real external repos.**

## What Happened

M002 finished the brownfield cleanup that M001 intentionally left open. The milestone started by extracting scan orchestration seams out of the validator monolith into `packages/skilllint/scan_runtime.py`, with import-identity tests proving the real CLI path uses those seams rather than parallel dead abstractions. That gave later slices a stable place to attach discovery and ownership behavior.

On top of those seams, the milestone introduced an explicit ownership model for validators. `ValidatorOwnership`, `VALIDATOR_OWNERSHIP`, and constraint-scope filtering made schema-backed validation, provider overlays, and lint-style rules traceable instead of implicit. This resolved the schema-vs-rule ambiguity that had made hard-failure behavior difficult to reason about.

With the ownership layer in place, M002 formalized scan target selection into three explicit modes: manifest-driven discovery when plugin manifests enumerate components, documented auto-discovery when manifests omit those arrays, and provider-structure discovery for `.claude/`, `.agent/`, `.agents/`, `.gemini/`, and `.cursor/` roots outside plugin context. Discovery behavior is now a contract rather than a side effect.

The milestone then used that clearer architecture to perform a truth pass against disputed rule families found in official external repos. FM004, FM007, and AS004 were downgraded from errors to warnings because Claude Code runtime behavior accepts those patterns and the prior hard-failure treatment was unjustified. FM003 and FM005 remained hard errors because missing frontmatter and genuine type mismatches are real schema violations. The warning-routing bug was also fixed so warning-severity issues land in the warnings list rather than the errors list.

To keep the architecture teachable, M002 added `docs/maintainer-extension-guide.md`, which gives maintainers a single reference with worked examples for schema updates, provider overlays, lint rules, and provenance metadata. That documentation is aligned to the post-refactor code layout rather than a stale conceptual model.

Finally, the milestone proved the whole integrated outcome through the real CLI path. External `uv run python -m skilllint.plugin_validator check ...` scans against `../claude-plugins-official`, `../skills`, and `../claude-code-plugins` matched the S04 truth-classification baseline. `scripts/verify-s06.sh` and `packages/skilllint/tests/test_external_scan_proof.py` now serve as operational regression proof that the refactor did not break user-facing behavior and that remaining hard failures are real, reviewable findings rather than linter hallucinations.

## Cross-Slice Verification

### Success criteria verification

- **Maintainers can tell whether a constraint belongs in schema, a provider overlay, or a lint rule without guessing — met.**
  - Evidence: S02 added explicit ownership routing via `ValidatorOwnership` and scope filtering.
  - Evidence: S05 added `docs/maintainer-extension-guide.md` with a decision tree and worked examples for schema updates, provider overlays, lint rules, and provenance metadata.

- **Directory scans select the right files based on manifest-driven enumeration, documented auto-discovery, or provider-known directory structure depending on scan root — met.**
  - Evidence: S03 implemented `ScanDiscoveryMode`, `detect_discovery_mode()`, manifest discovery helpers, and structure discovery helpers.
  - Evidence: `packages/skilllint/tests/test_discovery_modes.py` passed with 16 tests.

- **Official external repo scans no longer produce unjustified schema/frontmatter hard failures; any remaining hard failures are explainable and reviewable as likely real findings — met.**
  - Evidence: S04 downgraded FM004, FM007, and AS004 to warnings based on runtime evidence.
  - Evidence: S06 external scans produced exit code 0 for `../claude-code-plugins` and exit code 1 only where genuine FM003/FM005 findings remain.
  - Evidence: `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` and `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` document remaining hard failures for human review.

- **Maintainer docs include concrete worked examples for schema updates, provider overlays, lint rules, and provenance metadata — met.**
  - Evidence: S05 created `docs/maintainer-extension-guide.md` and verified the presence of all required sections and real file references.

- **The real `uv run skilllint check ...` path is used to prove the milestone, not just internal helper tests — met.**
  - Evidence: S04 and S06 both used `uv run python -m skilllint.plugin_validator check ...` against external repos.
  - Evidence: `scripts/verify-s06.sh` exits 0 and `packages/skilllint/tests/test_external_scan_proof.py` passes 9 tests.

### Definition of done verification

- **All slices complete — met.**
  - Evidence: S01-S06 summaries all exist under `.gsd/milestones/M002/slices/`.

- **Internal validator boundaries are wired into the real CLI path rather than existing as parallel abstractions — met.**
  - Evidence: S01 import-identity tests prove CLI aliases point to the extracted `scan_runtime.py` functions.

- **Directory scanning behaves correctly for plugin manifests, plugin auto-discovery, and structure-only provider trees — met.**
  - Evidence: S03 discovery-mode implementation plus 16 passing contract tests.

- **Official external repo scans no longer produce unjustified schema/frontmatter hard failures — met.**
  - Evidence: S04 severity downgrades and S06 external CLI proof.

- **Remaining official-repo hard failures are surfaced as reviewable findings rather than silently absorbed — met.**
  - Evidence: S04 and S06 findings reports preserve FM003/FM005 failures with file paths and review recommendations.

- **Maintainer docs with worked examples exist for schema updates, provider overlays, lint rules, and provenance metadata — met.**
  - Evidence: `docs/maintainer-extension-guide.md` created and UAT checks passed in S05.

- **Final integrated scan verification passes through the real `skilllint check` entrypoint — met.**
  - Evidence: `bash scripts/verify-s06.sh` exits 0 and `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` passes.

### Cross-slice integration checks

- `packages/skilllint/tests/test_scan_runtime.py` — 24 seam-boundary tests passed.
- `packages/skilllint/tests/test_ownership_routing.py` — 8 ownership-routing tests passed.
- `packages/skilllint/tests/test_discovery_modes.py` — 16 discovery-contract tests passed.
- `packages/skilllint/tests/test_rule_truth.py` — 11 rule-truth tests passed.
- `uv run pytest packages/skilllint/tests/ -q --no-cov` in S04 — 708 passed, 1 skipped.
- `bash scripts/verify-s06.sh` — passed.
- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — 9 passed.

No roadmap success criterion or definition-of-done item remained unmet.

## Requirement Changes

- R012: active → validated — S01 extracted `scan_runtime.py` seams and proved runtime wiring with 24 seam tests.
- R013: active → validated — S02 ownership routing plus S04/S06 severity and exit-code proof cleanly separated schema validation from lint validation.
- R014: active → validated — S02 made ownership and scope explicit, and S05 documented the extension model.
- R015: active → validated — S03 implemented manifest-driven discovery and covered it with contract tests.
- R016: active → validated — S03 implemented documented auto-discovery and covered it with contract tests.
- R017: active → validated — S03 implemented structure-based provider discovery and covered it with contract tests.
- R018: active → validated — S04/S06 proved official repos no longer fail hard on unjustified FM004/FM007/AS004 patterns.
- R019: active → validated — S04 produced evidence-backed rule classification and S06 preserved findings for review.
- R020: active → validated — S05 delivered worked schema-update documentation.
- R021: active → validated — S05 delivered worked provider-overlay documentation.
- R022: active → validated — S05 delivered worked lint-rule documentation.
- R023: active → validated — S05 delivered provenance-metadata documentation.
- R024: active → validated — S06 proved behavior via real external CLI scans.
- R025: active → validated — S06 proved user-facing CLI continuity after the internal refactor.

## Forward Intelligence

### What the next milestone should know
- The real compatibility baseline now lives in two places: the code-level truth classification in `packages/skilllint/plugin_validator.py` and the operational proof in `scripts/verify-s06.sh` plus `packages/skilllint/tests/test_external_scan_proof.py`. If a future milestone changes rule severity or discovery behavior, update both.
- `docs/maintainer-extension-guide.md` is now the single maintainer-facing reference for extension work. New schema, overlay, or rule changes should keep that guide aligned rather than letting docs drift again.
- The external findings left after M002 are intentional visibility, not unfinished linter cleanup. Future work should treat them as upstream issues unless new evidence overturns D015 or D016.

### What's fragile
- `plugin_validator.py` still retains deep-coupled reporting and `_run_validation_loop` behavior from the brownfield design — S01 explicitly left this in place, so future extractions must account for that coupling rather than assuming the monolith is fully gone.
- External proof paths are relative (`../claude-plugins-official`, `../skills`, `../claude-code-plugins`) — if neighboring repos move, `scripts/verify-s06.sh` and external proof tests will fail even if the linter is correct.

### Authoritative diagnostics
- `bash scripts/verify-s06.sh` — best end-to-end milestone regression check because it exercises the real CLI path against all three external repos and asserts expected exit codes.
- `uv run pytest packages/skilllint/tests/test_external_scan_proof.py -v --no-cov` — best structured regression surface for external behavior because it verifies error/warning families and strips ANSI formatting safely.
- `uv run pytest packages/skilllint/tests/test_rule_truth.py -v --no-cov` — best guardrail for future rule-severity changes because it locks the current truth classification.
- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` and `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — best place to inspect why remaining hard failures are still visible.

### What assumptions changed
- The milestone began with the risk that many official-repo hard failures might reflect stale or hallucinated linter constraints — the evidence showed FM004, FM007, and AS004 were unjustified as errors, but FM003 and FM005 remained genuine schema violations.
- The repo started M002 with discovery behavior spread across implicit code paths — by the end, discovery is an explicit three-mode contract with dedicated tests.
- The validator was assumed to need a broad monolith breakup all at once — in practice, extracting pure seams first and leaving deeply coupled reporting/validation-loop logic in place was the sustainable path.

## Files Created/Modified

- `packages/skilllint/scan_runtime.py` — extracted scan orchestration seams and explicit discovery-mode logic.
- `packages/skilllint/plugin_validator.py` — added ownership routing, constraint-scope filtering, and evidence-backed severity classification.
- `packages/skilllint/tests/test_scan_runtime.py` — seam-boundary and runtime-wiring regression coverage.
- `packages/skilllint/tests/test_ownership_routing.py` — ownership-routing regression coverage.
- `packages/skilllint/tests/test_discovery_modes.py` — discovery-contract regression coverage.
- `packages/skilllint/tests/test_rule_truth.py` — severity and warning-routing regression coverage.
- `packages/skilllint/tests/test_external_scan_proof.py` — external CLI regression coverage against official repos.
- `docs/maintainer-extension-guide.md` — maintainer documentation with worked extension examples.
- `scripts/verify-s06.sh` — end-to-end external scan verification script.
- `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md` — evidence-backed rule-truth findings report.
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — final external scan findings report.
