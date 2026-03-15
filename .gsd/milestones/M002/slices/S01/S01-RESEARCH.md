# M002/S01 Research: Validator seam map and boundary extraction

## Overview
This slice focuses on decomposing the monolithic `plugin_validator.py` and preparing internal boundaries for the rest of the M002 milestone. The monolith currently houses numerous validators and scan orchestration logic, making rule ownership and provider-specific behavior difficult to trace.

## Requirements Coverage
- R012: Decompose remaining validator monolith into explicit layers.

## Research Findings

### Monolith Surface Analysis
I examined `packages/skilllint/plugin_validator.py` and discovered it is not just a validator registry/runner — it contains the core implementation for:
- Registry management (via `_ADAPTERS` and `load_adapters`).
- File type classification (`FileType.detect_file_type`).
- Orchestration (`ProgressiveDisclosureValidator`, `InternalLinkValidator`, `NamespaceReferenceValidator`, etc. are defined *inside* the file).
- Error definitions (`ErrorCode` enum).
- Utility functions (YAML parsing/dumping, fixers).

The actual CLI entrypoint appears to rely on these combined responsibilities, illustrating precisely why this "monolith" is a maintenance risk for M002 boundaries.

### Validator Breakdown
The following classes are currently bundled in `plugin_validator.py`:
- `ProgressiveDisclosureValidator`
- `InternalLinkValidator`
- `NamespaceReferenceValidator`
- `SymlinkTargetValidator`
- `FrontmatterValidator`
- `NameFormatValidator`
- `DescriptionValidator`
- `ComplexityValidator`
- `PluginRegistrationValidator`
- `PluginStructureValidator`
- `HookValidator`

Each of these should ideally reside in a dedicated rule or validator module, allowing the orchestration layer to remain clean and agnostic of specific rule details.

### Orchestration and Scan Orchestration
The scan logic is currently mixed with validator logic. To meet the M002 requirements, the "scan orchestration" must be separated from "rule validation" to permit the three scan-target selection modes (manifest, auto-discovery, structure-only) to coexist clearly.

## Risks and Unknowns
- Refactoring `plugin_validator.py` threatens the stability of the real CLI entrypoint. Integration tests in `packages/skilllint/tests/test_cli.py` must be used during refactoring to prevent regressions.
- The `ErrorCode` definitions remain a central point of dependency; they may need to be moved to a stable shared location before validator extraction proceeds.

## Proposed Strategy
1.  **Extract Constants & ErrorCodes:** Move `ErrorCode` and shared constants to a permanent home (e.g., `constants.py` or `errors.py`).
2.  **Move Validators:** Migrate each validator class defined in `plugin_validator.py` into `packages/skilllint/rules/` or a new `packages/skilllint/validators/` directory.
3.  **Extract Orchestration:** Define an explicit `ValidatorRegistry` or similar seam that manages validator lookup, keeping `plugin_validator.py` as solely the CLI-entry/orchestration layer.
4.  **Verification:** Ensure all existing unit tests in `packages/skilllint/tests/` still pass after validator migration.
