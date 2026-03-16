# S04 — Research: Official-repo hard-failure truth pass

## Summary

The current `skilllint` validator is enforcing strict schema rules (e.g., `FM005`) that are triggering hard failures on official external plugins/skills. These failures are often due to missing or ill-formatted argument-hint strings in YAML frontmatter. Given the requirement to treat official repo failures as potential linter defects, these hard failures need to be re-evaluated as either genuine schema violations, legacy constraints that should be relaxed, or recommendation-level findings.

The goal of this slice is to classify these `FM005` (and other high-frequency) hard failures against documented ecosystem expectations, identifying whether the linter is being too rigid or if the official repositories need updates to match newer spec requirements.

## Recommendation

First, classify current "hard failure" rule families by their frequency, scope, and evidentiary support (docs vs. implicit code enforcement). Second, perform a truth-check on `FM005` by comparing the validator's strict string expectation against existing frontmatter in the official repos. Finally, propose a classification model that allows us to downgrade these findings or surface them as reviewable findings instead of blocking CLI hard failures.

## Implementation Landscape

### Key Files

- `packages/skilllint/plugin_validator.py` — orchestrator of validation loops; will need to incorporate the classification logic developed here.
- `packages/skilllint/frontmatter_validator.py` — likely where `FM005` enforcement lives; this is where the strictness will be relaxed or downgraded.
- `packages/skilllint/rule_registry.py` — where the rule metadata (severity/scoping) and authority classification should live.

### Build Order

1. **Rule Frequency Audit** — Run `skilllint` over all official repos and aggregate the failure frequency by rule identifier (`FM005`, etc.).
2. **Fact Gathering** — For `FM005`, compare the linter's expectation against a sample of official repo failures to verify if the linter is hallucinating, outdated, or merely stricter than reality.
3. **Classification Strategy** — Create a classification map (Justified/Legacy/Recommendation/Hallucination) for the common failures.
4. **Integration** — Wire this classification into `plugin_validator` so that findings can be selectively promoted/demoted based on their truth-classification rather than global strictness.

### Verification Approach

1. Run the validator against `../skills`, `../claude-plugins-official`, and `../claude-code-plugins`.
2. Inspect findings to ensure that downgrading `FM005` to a recommendation surface (if that's the decision) still triggers findings but does not hard-fail the scan.
3. Verify that the CLI output explicitly distinguishes these findings as "reviewable surface" versus "hard failures".

## Constraints

- Official repo scans scan MUST NOT be forced clean during this slice.
- Maintain existing scan target selection behavior (as established in S03).
- Must adhere to the ownership model (Schema vs Lint) established in S02 (hard failures vs second-level findings).

## Common Pitfalls

- **Incorrectly classifying a genuine validation failure as an linter error** — Always verify the linter expectation with the official spec before downgrading.
- **Over-generalizing the fix** — Avoid globally downgrading a rule if only one provider repo is violating it; look for provider-specific scopes.

## Open Risks

- We might discover that the "hallucinated" constraints are actually expected by newer Claude Code versions, making it risky to downgrade.
- We might find that the validators are so tightly coupled that downgrading `FM005` requires deeper refactoring than expected.

## Sources

- Original requirement: M002/M002-CONTEXT.md
- Active Requirements: R018, R019, R024, R025
