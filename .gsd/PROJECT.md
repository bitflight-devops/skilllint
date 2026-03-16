# Project

## What This Is

This repository contains `skilllint`, a Python-based linter for agent skill formats, plus GSD planning artifacts for evolving the project. It validates skill and plugin content across provider ecosystems, loads bundled versioned provider schemas, and reports rule authority/provenance so maintainers can trace why a constraint exists.

## Core Value

The one thing that must work is trustworthy detection: `skilllint` should discover the right files, apply the right schema and rule boundaries, and report real issues with traceable authority — without hallucinated constraints or ecosystem-incompatible hard failures.

## Current State

- M001 is complete: `skilllint` validates provider-specific skill content using versioned bundled schemas and rule authority metadata.
- M002 is complete: scan orchestration, ownership routing, discovery behavior, rule-truth classification, maintainer docs, and external CLI proof are all in place.
- The repo is primarily Python/CLI/test oriented, with the main package under `packages/skilllint/`.
- `packages/skilllint/scan_runtime.py` now owns explicit scan/discovery seams, while `plugin_validator.py` still contains some deeper validation-loop and reporting coupling left for later cleanup.
- Real-world scans against external Claude ecosystem repos now correctly distinguish genuine schema violations (FM003, FM005) from runtime-accepted patterns (FM004, FM007, AS004). Exit codes reflect only genuine errors.
- Maintainers now have `docs/maintainer-extension-guide.md` as the authoritative extension-path reference.
- Requirements are tracked explicitly in `.gsd/REQUIREMENTS.md`.

## Architecture / Key Patterns

- Python package under `packages/skilllint/` with CLI-oriented validation flows and strong pytest coverage.
- Provider adapters under `packages/skilllint/adapters/` expose platform-specific path patterns, applicable rules, constraint scopes, and schema access.
- Bundled provider schemas live under `packages/skilllint/schemas/<provider>/vN.json` and load through packaged-resource paths.
- Rule authority and provenance are surfaced through `packages/skilllint/rule_registry.py`.
- GSD artifacts under `.gsd/` track milestone context, roadmap, decisions, requirements, and execution state.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Versioned Provider Schema and Rule Authority Pipeline — Provider-aware validation with versioned bundled schemas, provenance, and packaged runtime proof.
- [x] M002: Validator Decomposition and Scan-Truth Hardening — Split remaining validator responsibilities, corrected scan/discovery behavior, classified disputed rule truth with evidence, added maintainer extension docs, and proved behavior through real external CLI scans.
  - [x] S01: Validator seam map and boundary extraction
  - [x] S02: Constraint ownership routing cleanup
  - [x] S03: Scan target discovery contract
  - [x] S04: Official-repo hard-failure truth pass
  - [x] S05: Maintainer extension-path documentation
  - [x] S06: External scan proof and findings report
