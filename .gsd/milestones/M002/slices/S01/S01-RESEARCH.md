# Research: M002/S01 — Validator seam map and boundary extraction

**Date:** 2026-03-15
**Status:** Mapped for S01 decomposition

## 1. Goal
Map the current monolithic `packages/skilllint/plugin_validator.py` responsibilities and identify clean internal seams to enable extraction of scan orchestration, schema validation, lint-rule execution, and reporting into separate boundaries.

## 2. Requirements Alignment
- **R012:** Primary owner. This slice initiates the decomposition of the brownfield monolith.

## 3. Scope & Boundaries
- **In-Scope:**
  - Audit existing `plugin_validator.py` entrypoints and dependencies.
  - Map current responsibilities: Scan orchestration vs. validation vs. reporting.
  - Define clear module boundaries for potential extraction.
- **Out-of-Scope:**
  - Actual extraction (S01 production logic).
  - Rule-truth classification (S04).
  - Scan discovery logic implementation (S03).

## 4. Key Investigations & Findings

### 4.1. Monolith Audit
- `packages/skilllint/plugin_validator.py` is the central hub.
- It appears to contain:
  1. CLI entrypoint logic.
  2. Recursive directory traversal/file filtering (scan orchestration).
  3. Orchestration of validation (calling various validators).
  4. Reporting/formatting of findings.
  5. Interaction with platform adapters.

### 4.2. Identified Seams
- **Scan/Discovery layer:** Logic that decides which files to validate (R016/R017).
- **Validation Engine:** Coordination of schema vs. semantic rules (R013).
- **Adapter layer:** Existing `packages/skilllint/adapters/` provides a seam for provider-specific logic.
- **Reporter layer:** Logic that converts validation findings to CLI output.

## 5. Risks & Unknowns
- Hidden, implicit dependencies between reporting and validation logic might make extraction fragile.
- Some validation logic might be deeply nested in the directory traversal logic.

## 6. Skill Discovery
- Promising skills for project structure/architecture work:
  - `debug-like-expert`: Recommended for deep analysis of the validator monolith (already loaded).
  - No additional external skills needed for this internal architectural mapping work.

## 7. Next Steps
- Implement module-boundary extraction in S01 production phase based on this map.
- Move reporting and scan orchestration out of `plugin_validator.py` to leave a leaner validator core.
