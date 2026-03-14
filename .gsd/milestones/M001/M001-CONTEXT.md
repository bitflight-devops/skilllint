# M001: Schema Registry and Rule Provenance — Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

## Project Description

Replace hardcoded structural limits and loosely-coupled provider rule sources with a schema-driven validation system. The new system should resolve a base schema plus provider overlays, expose typed runtime access through a central schema layer, attach explicit provenance to every rule and constraint, and progressively decompose the monolithic validator into the new structural, parser-format, and semantic rule layers.

## Why This Milestone

The current validator mixes hardcoded constants, bundled schema snapshots, parser heuristics, and provider-specific rules. That makes it hard to explain why a rule applies, hard to pin behavior to a schema version, easy for constraints to drift from upstream sources, and difficult to safely decompose behavior out of the monolith. This milestone establishes a durable contract layer and a decomposition path before more provider rules accumulate.

## User-Visible Outcome

### When this milestone is complete, the user can:

- inspect a rule and see which upstream standard, provider, or skilllint policy it comes from
- validate a skill file against a versioned schema stack that matches the target platform
- pin schema versions so older files can be linted against the contract they were written for

### Entry point / environment

- Entry point: `skilllint check` and rule catalog output
- Environment: local dev and CI
- Live dependencies involved: none for runtime validation; upstream vendor snapshots for schema refresh

## Completion Class

- Contract complete means: schema refs, composition rules, provenance metadata, and pinning config are covered by tests and checked artifacts
- Integration complete means: the main validator resolves and applies the right schema stack for at least one real provider path end-to-end
- Operational complete means: schema refresh and schema diff reporting work from the existing vendor/source collection pipeline

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- a skill targeting a provider extension path validates against the correct base-plus-overlay schema stack
- CLI output and/or rule catalog surfaces provenance and authority level for schema-backed and semantic rules
- a pinned schema version changes validation behavior predictably without code edits

## Risks and Unknowns

- Upstream providers may not publish official machine-readable schemas, forcing extraction from parser code or docs
- Existing validator code has two overlapping rule systems, which may complicate migration to schema-backed validation
- Some rules are semantic and cannot be expressed purely in JSON Schema, so the boundary must stay clear

## Existing Codebase / Prior Art

- `packages/skilllint/schemas/` — current bundled schema snapshots for some providers
- `packages/skilllint/plugin_validator.py` — current monolithic frontmatter/rule/fix execution path and primary decomposition target
- `packages/skilllint/rule_registry.py` — newer rule system with AS-series rules
- `scripts/fetch_platform_docs.py` — existing upstream doc/repo fetch and drift collection pipeline

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — Validation constraints and rules must expose provenance, authority level, and source references
- R002 — Every rule must be classified by enforcement layer so migration does not blur schema-backed, parser-format, and semantic checks
- R003 — Each migrated rule path must have end-to-end verification for fail, fix-when-supported, and explainability behavior

## Scope

### In Scope

- versioned schema layout and registry API
- base-plus-overlay schema composition
- rule provenance metadata model
- rule classification model and migration matrix
- decomposition map from monolithic validator responsibilities to target modules/layers
- decision trees and agent checklists for placing rules in the correct enforcement layer
- config support for schema version pinning
- schema refresh/extraction strategy tied to authoritative upstream sources
- end-to-end rule-path verification design for failure, auto-fix, and explanation surfaces

### Out of Scope / Non-Goals

- full migration of every legacy rule in one slice
- support for every provider-specific file type on day one
- replacing semantic lint rules with JSON Schema where that fit is poor

## Technical Constraints

- Prefer official schema or parser source over scraping prose docs
- Structural validation and semantic linting must remain distinct layers
- Users need stable pinning semantics for schema versions
- Lint failures must be resolved by improving design boundaries, data models, or helper contracts; suppression comments and lint-config weakening are out of bounds for this milestone
- Redesigns should move toward more modular, type-safe, and extensible Python 3.12+ structure with clear protocols, smaller units of responsibility, and separation that supports future provider growth

## Integration Points

- existing bundled schema files — need migration to versioned/provider-aware layout
- validator entrypoints — need schema resolution before field validation
- rule catalog/docs — need provenance surfaced to users

## Open Questions

- Which provider should be the first fully-wired overlay after `agentskills.io` — current best candidate is Claude Code because the extension story is explicit
- How much of the current Pydantic model layer should be generated dynamically versus maintained as thin typed wrappers

## Required Planning Outputs For This Milestone

The milestone research and slice plans must produce all of the following:

1. **Rule classification matrix**
   - current rule/code path
   - whether it currently lives in the monolith, a split rule module, or both
   - enforcement layer: `schema_structural`, `parse_format`, `semantic`, or `cross_file`
   - target owner after migration
   - provenance source and authority level
   - whether auto-fix is supported

2. **Decision tree for rule placement**
   - how an agent decides whether a new or existing rule belongs in schema validation, parser-format validation, semantic linting, or cross-file checks
   - explicit examples for edge cases such as delimited strings, YAML-repair diagnostics, and description-quality rules

3. **Agent checklist for migration and review**
   - how to verify provenance
   - how to verify enforcement layer placement
   - how to verify pinning behavior when schema-backed
   - how to verify fix safety when fixable
   - how to verify explanation quality and traceability
   - how to verify that migrated logic was actually removed or narrowed in the monolith rather than duplicated indefinitely
   - how to treat lint failures as design problems and reject suppression-based fixes
   - how to check that redesigns improved modularity, type safety, and future extensibility rather than just moving code around

4. **Rule-path verification contract**
   - failing file fails for the right rule
   - fixable failing file is fixed when `--fix` is used
   - post-fix validation passes or degrades to remaining non-fixable issues only
   - short output references the rule clearly enough for follow-up
   - `skilllint rule <rule>` provides full explanation, provenance, and source path/reference

## Planning Gate: RT-ICA Adaptation

Before writing a slice plan or delegating implementation work for this milestone, run an RT-ICA-style completeness pass on the top-level goal and on any slice being decomposed.

### Required procedure

1. Reconstruct the goal in one sentence and define the observable success output.
2. Reverse-think prerequisites needed for success across these categories where relevant:
   - upstream source availability
   - existing validator/codepath inventory
   - schema composition semantics
   - provenance/user-facing explanation requirements
   - pinning/config behavior
   - verification and migration safety
3. For each prerequisite, classify it as:
   - `AVAILABLE` — explicitly present in code, docs, or collected artifacts
   - `DERIVABLE` — inferable with high confidence from current evidence; record basis
   - `MISSING` — not safely inferable
4. If anything is `MISSING`, do not invent the answer. Add an explicit unblock action instead:
   - research task
   - repo inspection task
   - upstream source audit
   - targeted user question if the answer cannot be derived internally
5. Planning may proceed with `APPROVED-WITH-GAPS` only when missing inputs are localized to dependent tasks and those unblock tasks are wired as dependencies.

### Output expectation

Each research or planning artifact for this milestone should make the following visible:
- completeness decision: `APPROVED-FOR-PLANNING`, `APPROVED-WITH-GAPS`, or `BLOCKED-FOR-PLANNING`
- missing inputs by dependency
- required unblock actions
- assumptions carried forward for any `DERIVABLE` item
