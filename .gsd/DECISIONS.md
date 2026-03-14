# Decisions

- 2026-03-14: Structural constraints should move toward versioned schema artifacts with explicit provenance instead of a Python `limits.py` constant file.
- 2026-03-14: Upstream truth should be sourced in this order: official schema, then official parser/validator source, then structured first-party examples, then prose docs as a last resort.
- 2026-03-14: Rule metadata must expose provenance and authority level so users can understand why a rule applies and justify disabling it when appropriate.
- 2026-03-14: GSD planning for schema migration should use an RT-ICA-style completeness pass: reverse prerequisites from the goal, classify inputs as available/derivable/missing, and create explicit unblock or discovery tasks instead of inventing requirements.
- 2026-03-14: The monolithic validator is a decomposition target, not a permanent compatibility center. Each slice should move owned logic out of the monolith into the new schema/rule structure where the boundary is understood and verified.
- 2026-03-14: Lint failures in migration work are design signals, not suppression opportunities. `# noqa`, `# type: ignore`, and linter-config weakening are banned for this restructuring work; fix the ownership, abstraction, or API shape instead.
- 2026-03-14: Redesign work must improve modularity, type safety, and extensibility. Favor Python 3.12+ patterns, explicit protocols/types, and SOLID-style boundary separation so future provider/schema expansion fits the architecture without re-centralizing logic.
