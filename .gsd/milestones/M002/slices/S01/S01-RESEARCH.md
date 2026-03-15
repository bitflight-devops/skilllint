# S01: Validator seam map and boundary extraction — Research

## Objectives
- Map current validator monolithic responsibilities in `packages/skilllint/plugin_validator.py`.
- Identify extraction seams for schema validation, lint-rule execution, and reporting.
- Propose new internal module boundaries to reduce reliance on one dominant validator file.

## Findings
- `packages/skilllint/plugin_validator.py` acts as a "god file" containing validator protocols, concrete implementations, CLI entry point, result collection, and reporter classes.
- Validations are currently selected in `_get_validators_for_path` based on `FileType`.
- Reporters (`ConsoleReporter`, `CIReporter`, `SummaryReporter`) and CLI support functions (like `is_ignored`, `_frontmatter_requirement`) all live together alongside validation logic.
- Validator classes (`FrontmatterValidator`, `DescriptionValidator`, `PluginStructureValidator`, etc.) are heavily coupled with the orchestrating file's CLI logic and file type detection.

## Proposed Module Boundaries (Draft)
1. `packages/skilllint/validator/orchestrator.py`: CLI entry point, result gathering, and orchestrator logic.
2. `packages/skilllint/validator/registry.py`: Logic for mapping file types to validators (`_get_validators_for_path`).
3. `packages/skilllint/validator/reporters.py`: Reporter implementations (`Reporter` protocol and concrete classes).
4. `packages/skilllint/validator/rules`: Keep existing rule classes here or group them by responsibility (schema vs lint rules).
5. `packages/skilllint/validator/frontmatter.py`: Extract frontmatter logic, requirements, and validation.

## Next Steps
- Implement new modules incrementally.
- Update `packages/skilllint/plugin_validator.py` to import from/delegate to new modules.
- Ensure CLI entry point (`skilllint check`) remains functional.
