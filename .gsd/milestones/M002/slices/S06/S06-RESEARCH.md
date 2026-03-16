# Research — S06: External scan proof and findings report

**Date:** 2026-03-16

## Summary

This slice is the final functional verification of the milestone M002 architecture. It provides empirical proof that the refactored detection engine, scan discovery contracts, and rule truth classification successfully handle real-world plugin structures across official ecosystem repositories (`../skills`, `../claude-plugins-official`, `../claude-code-plugins`).

The recommendation is to execute a comprehensive integration scan against these targets, treating the output as the baseline for "truthful" detection. This will demonstrate that the linter correctly differentiates genuine schema errors (FM003/FM005) from runtime-accepted warnings (FM004/FM007/AS004) while confirming the discovery logic correctly routes across manifest-driven and provider structure-only trees.

## Implementation Landscape

### Key Files

- `packages/skilllint/plugin_validator.py` — The unified point of execution. The verification will confirm that the extracted seams and classification logic operate correctly at the end of the real CLI invocation chain.
- `packages/skilllint/scan_runtime.py` — orchestrates discovery. Verification confirms that the three discovery modes (manifest, auto-discovery, structure-only) correctly resolve targets for the official repositories.
- `packages/skilllint/tests/test_cli.py` — Serves as the template for the verification suite, ensuring integration tests retain regression coverage for the CLI interface.

### Build Order

1. **Local integration scan** — Run `uv run skilllint check` against the three target directories (`../skills`, `../claude-plugins-official`, `../claude-code-plugins`) to establish the baseline of detections.
2. **Review of findings** — Inspect the output to ensure exit codes (0 for warnings, 1 for errors) align with expectations and that warnings are properly flagged for human review.
3. **Regression suite enhancement** — Add an explicit integration test case that mirrors these external scans to prevent future divergence.

### Verification Approach

Execution of real CLI commands provides the empirical proof:
- `uv run skilllint check ../skills`
- `uv run skilllint check ../claude-plugins-official`
- `uv run skilllint check ../claude-code-plugins`

Success criteria is empirically observed through:
- Exit codes matching the truth pass classification (1 for upstream schema errors, 0 for otherwise).
- Presence of warnings for diagnostic-style findings (FM004, etc.).
- Absence of unjustified errors that block CI/CD or development workflows.

## Constraints

- Detection correctness is the priority; autofix behavior is explicitly out of scope for this milestone (D010).
- External repo scans must NOT force a clean state; findings must remain visible for review as long as they are evidence-backed (D011).
- The three discovery modes (manifest-driven, auto-discovery, structure-only) must remain distinct (D013).

## Open Risks

- The primary risk is that a "clean" verification scan might miss genuine errors or over-suppress warnings if the discovery logic misinterprets a new plugin structure not encountered in S03/S04. The plan is to manually verify scan outputs for unexpected omissions.

## Skills Discovered

- `skilllint` is the primary package, but the orchestrator relies on the `development-harness` skill for organizing this validation workflow if needed.

## Sources

- Milestone Roadmap: `.gsd/milestones/M002/M002-ROADMAP.md`
- Milestone Context: `.gsd/milestones/M002/M002-CONTEXT.md`
- S04 Findings: `.gsd/milestones/M002/slices/S04/S04-FINDINGS.md`
