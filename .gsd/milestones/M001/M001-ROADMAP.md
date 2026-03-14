# M001: Schema Registry and Rule Provenance

**Vision:** `skilllint` validates files against versioned schema stacks with explicit provenance, so users can see exactly why a rule applies, pin the schema contract that matches their files, and rely on a progressively decomposed validator instead of one monolithic rule engine.

## Success Criteria

- Users can inspect a rule and see provider, rule kind, authority level, and source reference.
- `skilllint` can resolve a base schema plus a provider overlay for at least one real platform path.
- Users can pin a schema version and get stable validation behavior against that pinned contract.
- Structural constraints no longer depend on an ad hoc `limits.py` file as the long-term source of truth.
- Agents have a decision tree and checklist that let them place, migrate, and verify rules consistently.
- For migrated rules, end-to-end verification proves failure behavior, auto-fix behavior when supported, and understandable explanation paths.
- Each completed slice measurably reduces logic ownership inside `plugin_validator.py` for the covered rule paths instead of creating permanent parallel implementations.
- Covered lint issues are eliminated by design changes rather than suppression comments or reduced lint strictness.
- The new structure is more modular, more type-safe, and easier to extend for future providers and schema versions using modern Python 3.12+ design patterns.

## Key Risks / Unknowns

- Some providers may only expose prose docs, not official schemas or parser code — extraction quality varies by provider.
- Existing validator paths are partially duplicated — migration could create inconsistent behavior if not cut over carefully.
- Semantic rules may get mixed back into schema artifacts unless boundaries are enforced.
- Rule placement may stay inconsistent unless agents have an explicit decision tree and migration checklist.
- User-facing explanation paths may drift unless short-form and full-detail rule outputs are verified end-to-end.
- The monolith may become a shadow implementation unless each slice includes explicit logic extraction or narrowing for the rule paths it covers.

## Proof Strategy

- Upstream source quality → retire in S01 by proving one provider stack can be resolved from a canonical base plus documented overlay metadata.
- Rule placement risk → retire in S01 by producing and validating a decision tree plus rule classification matrix against the existing patchwork validator paths.
- Monolith decomposition risk → retire incrementally by requiring each slice to define which `plugin_validator.py` responsibilities move, which remain temporarily, and what compatibility shim is removed or narrowed.
- Validator migration risk → retire in S02 by proving the active validator uses the resolved schema stack for real files without collapsing parse-format or semantic rules into schema checks.
- User explainability risk → retire in S03 by proving provenance, short rule references, and `skilllint rule <rule>` detail paths are visible and testable from user-facing outputs.
- Planning completeness risk → retire in S01 by running RT-ICA-style prerequisite analysis before slice planning and converting missing inputs into explicit unblock work instead of assumptions.

## Verification Classes

- Contract verification: schema registry tests, schema composition tests, config parsing tests, provenance metadata checks, rule classification/decision-tree checks, and lint-clean helper/module boundaries without suppressions
- Integration verification: `skilllint check` against real fixture files for base and overlaid providers, including fail/fix/explain rule-path tests
- Operational verification: schema refresh/extraction run against existing source collection workflow or checked vendor artifacts
- UAT / human verification: inspect short CLI rule output and `skilllint rule <rule>` output to confirm provenance is understandable and traceable
- Design verification: changed modules show narrower responsibilities, stronger typing/contracts, and clearer extension seams than the monolithic path they replace

## Milestone Definition of Done

This milestone is complete only when all are true:

- schema registry, provenance model, rule classification model, and pinning support are implemented for the first real provider path
- validator entrypoints actually consume resolved schemas instead of parallel hardcoded limits for covered structural constraints
- parser-format and semantic rules are explicitly mapped and not silently folded into schema validation
- a decision tree and agent checklist exist for rule placement, migration, and verification
- for every covered rule path, the monolithic validator has either been reduced to a compatibility shim or had direct logic removed/narrowed in favor of the new owner
- migration-related lint issues are resolved through refactoring or better type/boundary design, with no suppression comments added
- redesigned paths demonstrate narrower responsibilities, stronger type contracts, and cleaner extension seams than the monolithic code they replace
- the real CLI entrypoint is exercised with pinned and default schema paths
- migrated rule paths are exercised end-to-end for fail, fix-when-supported, and explanation behavior
- success criteria are re-checked against runtime behavior and emitted artifacts
- final integrated acceptance scenarios pass

## Requirement Coverage

- Covers: R001, R002, R003
- Partially covers: none
- Leaves for later: additional provider migrations beyond the first overlay
- Orphan risks: none

## Slices

- [ ] **S01: Rule Classification and Provider Schema Stack** `risk:high` `depends:[]`
  > After this: one real provider path is represented as a versioned base-plus-overlay schema stack, and the existing rules are classified by enforcement layer with a decision tree plus an explicit decomposition map out of the monolith.
- [ ] **S02: Validator Cutover for Structural Constraints** `risk:medium` `depends:[S01]`
  > After this: `skilllint check` validates covered structural constraints through the schema registry while parser-format and semantic rules remain explicitly separate, and the covered structural logic is narrowed or removed from the monolith.
- [ ] **S03: User-Facing Provenance, Pinning, and Rule-Path Verification** `risk:medium` `depends:[S02]`
  > After this: users can see why a rule applies, pin the schema version used during validation, and follow rule output from short CLI form to full `skilllint rule <rule>` detail.

## Boundary Map

### S01 → S02

Produces:
- schema ref format for provider/kind/version
- resolved schema loader for base-plus-overlay composition
- field-level provenance metadata contract
- rule classification matrix
- decision tree for rule placement across schema, parser-format, semantic, and cross-file layers

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- normalized provenance model usable by CLI and docs
- versioned schema storage layout and latest-resolution rules
- agent checklist for migration and verification
- rule-path verification contract for fail/fix/explain behavior

Consumes:
- nothing (first slice)
