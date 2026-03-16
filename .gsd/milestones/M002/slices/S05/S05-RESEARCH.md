# S05 — Maintainer extension-path documentation - Research

**Date:** 2026-03-15

## Summary

This slice addresses R020, R021, R022, and R023 by creating concrete, worked examples of the primary extension paths for `skilllint`. With the ownership boundaries established in M002/S01-S04, maintainers need clear, truthful examples that reflect the post-refactor architecture rather than the brownfield monolith.

The recommended approach is to create a new dedicated documentation file `docs/maintainer-extension-guide.md` which will serve as the source of truth, incorporating real-world snippets from existing `adapters/`, `rules/`, and `schemas/` directories.

## Recommendation

Create `docs/maintainer-extension-guide.md` with four core sections:
1. **Schema Updates:** How to add a versioned schema to `packages/skilllint/schemas/<provider>/vN.json`.
2. **Provider Overlays:** How to implement a new `PlatformAdapter` and register it in `packages/skilllint/adapters/registry.py`.
3. **Lint Rules:** How to add a new rule in `packages/skilllint/rules/`, specifying its `ValidatorOwnership` (SCHEMA/LINT) and registering it.
4. **Provenance Metadata:** How to add authoritative metadata to schemas/rules using the structured format established in M001.

This will be the standard reference for all new extensions, ensuring maintainers perform extension tasks in the correct architectural layer.

## Implementation Landscape

### Key Files

- `docs/maintainer-extension-guide.md` — The new documentation surface.
- `packages/skilllint/adapters/registry.py` — Location for registering new adapters.
- `packages/skilllint/rules/` — Location for adding new lint rules.
- `packages/skilllint/schemas/` — Location for adding new schemas.

### Build Order

1. Draft the guide `docs/maintainer-extension-guide.md` using existing patterns as examples.
2. Ensure the guide accurately references the new module boundaries and ownership model from S02/S03.
3. Verify the guide by tracing a hypothetical "Add a dummy rule" process against the actual files.

### Verification Approach

- Manual review of the documentation for clarity and accuracy.
- Cross-referencing against real files in the repository to ensure examples reflect current realities.
- Ensure the guide mentions where to update `packages/skilllint/plugin_validator.py` if a new validator is added.

## Common Pitfalls

- **Documenting old patterns:** Ensure the guide does *not* suggest modifying `plugin_validator.py` monolithically but rather the partitioned registry and rules modules.
- **Ambiguous ownership:** Clearly distinguish between rule-based findings and schema-based errors.

## Skills Discovered

- `/claude-code-setup/claude-automation-recommender` (Useful for checking if we should add a skill for guide maintenance)
- `/plugin-creator/claude-plugins-reference-2026` (Relevant reference)

Slice S05 researched.