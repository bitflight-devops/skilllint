---
estimated_steps: 6
estimated_files: 1
---

# T01: Write maintainer extension guide with four worked examples

**Slice:** S05 — Maintainer extension-path documentation
**Milestone:** M002

## Description

Create `docs/maintainer-extension-guide.md` — the single reference for extending skilllint. Four worked examples cover schema updates, provider overlays, lint rules, and provenance metadata. Each example references real files in the post-refactor codebase and teaches the ownership/discovery/severity model.

## Steps

1. Create `docs/maintainer-extension-guide.md` with a header and a "Where does this belong?" decision tree:
   - Schema-backed shape/type validation → schema JSON + `ValidatorOwnership.SCHEMA`
   - Provider-specific behavior → adapter in `adapters/<provider>/` + register in `adapters/registry.py`
   - Cross-platform quality/style rule → rule in `rules/` + `ValidatorOwnership.LINT`
   - Traceability metadata → `authority` dict in schema or rule

2. Write **Section 1: Adding a Schema Update**. Use `packages/skilllint/schemas/claude_code/v1.json` as the real template. Show:
   - Where versioned schema files live: `packages/skilllint/schemas/<provider>/vN.json`
   - How to add a new field or constraint to the JSON schema
   - That schema validators produce `ValidatorOwnership.SCHEMA` (hard errors)
   - How to test: `uv run pytest packages/skilllint/tests/ -k frontmatter`

3. Write **Section 2: Adding a Provider Overlay (New Adapter)**. Use `packages/skilllint/adapters/claude_code/` as real template. Show:
   - The `PlatformAdapter` protocol from `packages/skilllint/adapters/protocol.py` (five methods: `id`, `path_patterns`, `applicable_rules`, `constraint_scopes`, `validate`)
   - Creating a new adapter directory `packages/skilllint/adapters/<new_provider>/`
   - Registering via entry points in `pyproject.toml` under `[project.entry-points."skilllint.adapters"]`
   - How `load_adapters()` in `packages/skilllint/adapters/registry.py` discovers it
   - Reference `ScanDiscoveryMode` from `packages/skilllint/scan_runtime.py` — explain that the new provider directory name should be added to structure-based discovery if it's a provider root directory

4. Write **Section 3: Adding a New Lint Rule**. Use `packages/skilllint/rules/as_series.py` as real template. Show:
   - File location: `packages/skilllint/rules/`
   - Using `@skilllint_rule` decorator from `packages/skilllint/rule_registry.py`
   - Adding the validator to `VALIDATOR_OWNERSHIP` dict in `packages/skilllint/plugin_validator.py` with `ValidatorOwnership.LINT`
   - Adding to `VALIDATOR_CONSTRAINT_SCOPES` dict
   - Choosing severity: reference S04 classification — `error` only for genuine schema violations, `warning` for style/preference rules
   - How to test: `uv run pytest packages/skilllint/tests/ -k <rule_code>`

5. Write **Section 4: Adding Provenance Metadata**. Show:
   - The `authority` dict structure: `{"origin": "...", "reference": "..."}` 
   - Where it lives in schema JSON files (top-level `authority` key)
   - Where it lives in rule definitions (returned in violation dicts)
   - Why it matters: traceability from violation output back to authoritative source (D002, D005)

6. Verify all file paths referenced in the guide actually exist in the repo. Run:
   ```bash
   test -f docs/maintainer-extension-guide.md
   grep -c "ValidatorOwnership" docs/maintainer-extension-guide.md
   grep -c "PlatformAdapter" docs/maintainer-extension-guide.md
   grep -c "ScanDiscoveryMode\|detect_discovery_mode" docs/maintainer-extension-guide.md
   grep -c "authority" docs/maintainer-extension-guide.md
   ```

## Must-Haves

- [ ] Decision tree at top: "schema vs provider overlay vs lint rule vs provenance"
- [ ] Schema update example referencing `packages/skilllint/schemas/claude_code/v1.json`
- [ ] Provider overlay example referencing `PlatformAdapter` protocol and entry-point registration
- [ ] Lint rule example referencing `as_series.py`, `@skilllint_rule`, `VALIDATOR_OWNERSHIP`, severity guidance
- [ ] Provenance metadata example showing `authority` dict structure
- [ ] All referenced file paths are real (not invented)

## Verification

- `test -f docs/maintainer-extension-guide.md` passes
- All five grep checks return ≥1
- No file path in the guide points to a nonexistent file

## Inputs

- `packages/skilllint/schemas/claude_code/v1.json` — real schema template
- `packages/skilllint/adapters/protocol.py` — PlatformAdapter protocol definition
- `packages/skilllint/adapters/registry.py` — adapter loading mechanism
- `packages/skilllint/rules/as_series.py` — real lint rule template
- `packages/skilllint/plugin_validator.py` — ValidatorOwnership enum at line ~358, VALIDATOR_OWNERSHIP dict at ~371, VALIDATOR_CONSTRAINT_SCOPES
- `packages/skilllint/scan_runtime.py` — ScanDiscoveryMode enum, detect_discovery_mode()
- `packages/skilllint/rule_registry.py` — @skilllint_rule decorator

## Expected Output

- `docs/maintainer-extension-guide.md` — Complete maintainer extension reference with four worked examples and decision tree
