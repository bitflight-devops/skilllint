# M002: Validator Decomposition and Scan-Truth Hardening — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

## Project Description

This milestone continues `skilllint` architecture work. The goal is not to add a new product direction, but to finish separating concerns that still live too close together in the brownfield validator. The user wants the remaining validator monolith split apart, schema validation cleanly separated from lint-rule validation, provider-specific behavior made easy to trace, and maintainer documentation brought back in line with the actual architecture.

Just as importantly, the user wants this milestone grounded in reality. We already ran real CLI scans against `../skills`, `../claude-plugins-official`, and `../claude-code-plugins` and saw many hard failures around frontmatter and shape rules. The user's instruction is to blame the linter first: each disputed rule should be treated as potentially wrong, legacy, provider-specific, recommendation-only, or hallucinated until proven otherwise. Official repo failures are not automatic proof that the repos are wrong.

The scan model also needs to be made explicit. When `skilllint` is given a directory, it must decide what to scan based on the real structure under that directory. If a plugin manifest explicitly lists agents, commands, skills, or hooks, the manifest should drive scan target selection. If those arrays are absent, `skilllint` should follow the documented plugin auto-discovery protocol. If the scan root is a provider config tree like `.claude/`, `.agent/`, `.agents/`, `.gemini/`, or `.cursor/`, there is no plugin manifest to read, so discovery should be based on known provider structure instead.

## Why This Milestone

M001 established provider-aware schemas and rule authority metadata, but it did not finish the brownfield cleanup. The current repo still risks drifting back into a monolithic validator shape, and external scans show that some hard-failure behavior may reflect outdated constraints, implementation assumptions, or unsourced rules rather than current ecosystem truth. This milestone is the right next step because architecture cleanup without detection truth would just reorganize confusion, and detection-truth work without architectural cleanup would leave the project hard to maintain.

## User-Visible Outcome

### When this milestone is complete, the user can:

- run `uv run skilllint check ../skills ../claude-plugins-official ../claude-code-plugins` and trust that hard failures reflect justified constraints rather than linter hallucinations or stale assumptions.
- inspect maintainer docs that show, with worked examples, how to add a schema update, provider overlay, new lint rule, and provenance metadata.
- understand what remaining hard failures still exist in the official repos after the truth pass, so they can review those findings instead of having the linter silently absorb them.

### Entry point / environment

- Entry point: `uv run skilllint check ...` and maintainer docs in the repo
- Environment: local dev in the `agentskills-linter` repo with neighboring external repos available on disk
- Live dependencies involved: local filesystem, packaged schema artifacts, external scan roots, and Claude Code CLI as a behavioral probe during investigation

## Completion Class

- Contract complete means: scan/discovery rules, schema-vs-rule boundaries, and provider/shared ownership are explicit in code and docs and are covered by tests and fixture checks.
- Integration complete means: the real CLI scan path correctly handles plugin manifests, plugin auto-discovery, and structure-only provider directory scans across internal and external repos.
- Operational complete means: external scan commands can be run locally and produce trustworthy hard-failure behavior plus a reviewable findings surface.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `skilllint` can scan the official external repos without unjustified schema/frontmatter hard failures.
- disputed rule families can be classified using current docs, runtime behavior, and implementation evidence as real, legacy, provider-specific, recommendation-only, or hallucinated.
- the post-refactor architecture still drives the real `skilllint check` entrypoint rather than living as a parallel unused structure.

## Risks and Unknowns

- The current hard failures in official repos may mix real repo issues with linter hallucinations — this matters because the milestone must not “fix” scans by hiding genuine findings.
- Discovery rules are likely implicit in current code and docs — this matters because manifest-driven scanning, auto-discovery, and structure-only scanning have to be made explicit without breaking brownfield behavior.
- Some constraints may be recommendations that the linter currently escalates to hard failures — this matters because real-world compatibility depends on correct severity and scope.
- Claude Code runtime behavior can provide strong evidence, but it is not the sole authority — this matters because runtime permissiveness and documented contract can diverge.

## Existing Codebase / Prior Art

- `packages/skilllint/plugin_validator.py` — brownfield validator entrypoint and likely center of remaining monolithic responsibility.
- `packages/skilllint/adapters/` — existing provider adapter seam for path patterns, applicable rules, constraint scopes, and schema access.
- `packages/skilllint/rule_registry.py` — current rule authority and provenance surface.
- `packages/skilllint/schemas/` — packaged provider schema artifacts already proven in M001.
- `packages/skilllint/tests/test_cli.py` — current CLI verification surface, including platform dispatch.
- `packages/skilllint/tests/test_provider_validation.py`, `test_provider_contracts.py`, `test_bundled_schema.py` — current provider-aware validation proof surfaces.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R012 — Decompose remaining validator monolith into explicit layers.
- R013 — Separate schema validation from lint-rule validation cleanly.
- R014 — Clarify provider-specific vs shared rule ownership.
- R015, R016, R017 — Correct scan target selection for manifest-driven, auto-discovery, and structure-only directory scanning.
- R018, R019 — Make hard failures in official-repo scans evidence-backed and reviewable.
- R020, R021, R022, R023 — Ship maintainer docs with worked examples.
- R024, R025 — Prove the real CLI still works through external scans after refactor.

## Scope

### In Scope

- Internal validator decomposition around real ownership boundaries.
- Scan target discovery rules for plugin and provider-directory scanning.
- Classification of disputed hard-failure rule families using evidence.
- External scan verification against `../skills`, `../claude-plugins-official`, and `../claude-code-plugins`.
- Maintainer documentation for extension paths with worked examples.

### Out of Scope / Non-Goals

- Ensuring autofix behavior is correct for the newly clarified rules.
- Silencing all warning-level findings in official repos.
- Expanding this milestone to Codex or OpenCode external repo validation yet.
- Adding unrelated new lint-rule families just because the architecture is being touched.

## Technical Constraints

- Detection correctness is the goal; autofix correctness is explicitly out of scope.
- Official repo failures should first be treated as possible linter mistakes, stale constraints, or mis-scoped rules before being treated as upstream repo defects.
- Manifest arrays, plugin auto-discovery, and provider structure-only scans must each remain distinct behaviors.
- The real `skilllint check` CLI path is the truth surface; refactors that do not wire into it do not count.

## Integration Points

- External scan roots: `../skills`, `../claude-plugins-official`, `../claude-code-plugins`
- Claude Code CLI docs and runtime behavior — used as investigation input for disputed constraints
- `packages/skilllint/adapters/` — provider routing and scan behavior
- `packages/skilllint/schemas/` — schema-backed detection path
- `packages/skilllint/tests/` — fixture and regression proof surfaces

## Open Questions

- Which of the current hard-failure families are truly schema/frontmatter constraints versus recommendations or stale assumptions? — Current thinking: S04 should classify by rule family, not by individual file only.
- How much of current scan target selection is already encoded in docs versus just living in code paths? — Current thinking: S03 should make the contract explicit in both code and docs.
- Should Claude CLI probing become a formal reusable harness in this milestone? — Current thinking: defer harness automation unless the investigation clearly justifies it.
