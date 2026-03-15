# S01-RESEARCH.md - Validator seam map and boundary extraction

## Overview
This research maps the current monolithic structure of `packages/skilllint/plugin_validator.py` to support the M002 milestone goal of decomposing the validator into explicit layers and seams.

## Findings
- **Monolithic Validator Structure**: Found that `packages/skilllint/plugin_validator.py` acts as a monolithic entrypoint containing multiple validator classes (`ProgressiveDisclosureValidator`, `InternalLinkValidator`, `NamespaceReferenceValidator`, etc.) all implementing a `validate(self, path: Path)` method.
- **Entrypoints**: The main validation entrypoints seem to be distributed across specialized classes rather than a single master validator. There's also a `validate_file` function and a `validate_with_claude` function, which might be the real integration points for the CLI.
- **Seams**: The `Validator(Protocol)` defined in the file provides a promising seam for implementing cleaner dependency injection and layer separation.
- **Dependency Issues**: Many validators are directly imported or included in the same file, making it hard to reason about shared versus provider-specific ownership.

## Risks & Unknowns
- **CLI Dependency**: Are callers using classes directly, or are they relying on the `validate_file` function? Need to confirm how `skilllint check` calls this module.
- **Hidden Coupling**: The shared dependencies within `plugin_validator.py` might be deeper than just class definitions (e.g., shared state, helper functions).
- **Registration**: How are these validators registered and chosen for a given file/plugin?

## Plan for S01
1. **Confirm CLI Entrypoint**: Investigate `packages/skilllint/tests/test_cli.py` and the CLI code to see how it invokes validation.
2. **Map Module Dependencies**: Analyze how the validators share dependencies.
3. **Draft Separation Strategy**: Move classes into individual files under `packages/skilllint/validators/` or equivalent, and update `plugin_validator.py` to act as an orchestrator/registry instead of a container.

## Deliverable Status
- [x] Initial research on validator monolith structure.
- [ ] Confirmation scan of scan orchestration seams.

## Next Steps
- Investigate scan orchestration logic.
- Plan internal module boundary extraction.
