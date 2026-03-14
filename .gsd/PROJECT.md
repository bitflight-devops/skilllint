# agentskills-linter

## Current State

`skilllint` is a linter for agent skill formats across multiple providers. The codebase currently mixes hardcoded validation limits, rule logic, provider-specific behavior, and documentation-derived constraints. Some rules now explicitly document provenance, but the structural constraint system is still split between Python constants, validator logic, and bundled schema snapshots.

## What The Project Is Becoming

The project is moving toward a schema-driven validation architecture:
- versioned provider schemas instead of ad hoc limits constants
- explicit provenance for every rule and constraint
- composition of base standards (for example `agentskills.io`) with provider-specific extensions (for example Claude Code)
- a clear split between schema-backed structural validation and semantic lint rules

## Immediate Focus

Build the schema registry and provenance system so structural rules can be sourced from versioned schemas, refreshed from authoritative upstream sources, and pinned by users when needed.
