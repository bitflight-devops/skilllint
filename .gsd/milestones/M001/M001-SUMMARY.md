---
milestone: M001
status: planned
updated: 2026-03-14
---

# M001 Summary

This milestone establishes a schema-driven validation foundation for `skilllint` without collapsing non-schema rules into the wrong layer. The goal is to replace hardcoded structural constraints with versioned schemas, support base-plus-overlay composition for provider extensions, classify rules by enforcement layer, attach explicit provenance to every rule and constraint so users can understand and justify enforcement decisions, and progressively decompose the monolithic validator as covered rule paths move into their new owners.

Planned slices:
- S01: Rule Classification and Provider Schema Stack
- S02: Validator Cutover for Structural Constraints
- S03: User-Facing Provenance, Pinning, and Rule-Path Verification
