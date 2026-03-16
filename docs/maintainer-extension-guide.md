# Maintainer Extension Guide

This guide explains how to extend skilllint with new schemas, provider adapters, lint rules, and provenance metadata. Use this when adding support for a new AI coding platform or enhancing validation capabilities.

## Where Does This Belong?

Before implementing, determine which extension path applies:

| Your Goal | Extension Path | Key Files |
|-----------|---------------|-----------|
| **Schema-backed shape/type validation** | Schema JSON + `ValidatorOwnership.SCHEMA` | `packages/skilllint/schemas/<provider>/vN.json` |
| **Provider-specific behavior** | Adapter in `adapters/<provider>/` + registry | `packages/skilllint/adapters/<provider>/` |
| **Cross-platform quality/style rule** | Rule in `rules/` + `ValidatorOwnership.LINT` | `packages/skilllint/rules/` |
| **Traceability metadata** | `authority` dict in schema or rule | Schema top-level key, rule decorator |

**Quick decision tree:**

1. Does the validation come from an official schema specification? → **Schema update**
2. Does it require platform-specific file patterns or behavior? → **Provider adapter**
3. Is it a style/quality rule that applies across platforms? → **Lint rule**
4. Do you need to trace where a validation requirement comes from? → **Provenance metadata**

---

## Section 1: Adding a Schema Update

Schema updates add or modify constraints that are backed by an official specification. These produce `ValidatorOwnership.SCHEMA` violations (hard errors that fail the build).

### Where Schema Files Live

Versioned schema files are stored in:

```
packages/skilllint/schemas/<provider>/vN.json
```

For example, `packages/skilllint/schemas/claude_code/v1.json` defines the Claude Code platform schema.

### Schema Structure

Each schema file has a top-level structure:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "skilllint/schemas/claude_code/v1.json",
  "title": "Claude Code Platform Schema v1",
  "version": "1.0.0",
  "platform": "claude_code",
  "provenance": {
    "authority_url": "https://docs.anthropic.com/claude-code",
    "last_verified": "2026-03-14",
    "provider_id": "claude_code"
  },
  "file_types": {
    "skill": { "fields": { ... } },
    "agent": { "fields": { ... } },
    "command": { "fields": { ... } },
    "plugin": { "fields": { ... } }
  }
}
```

### Adding a New Field Constraint

To add a new field or constraint:

1. **Locate the target `file_types` section** (e.g., `skill`, `agent`, `command`, `plugin`).

2. **Add or modify the field** with required metadata:

```json
"fields": {
  "new_field": {
    "required": false,
    "constraint_scope": "shared",
    "x-audited": {
      "date": "2026-03-15",
      "source": "docs/new-provider/spec.md"
    }
  }
}
```

3. **Set `constraint_scope` appropriately**:
   - `"shared"` — Applies to all platforms
   - `"provider_specific"` — Only applies when this provider's adapter is active

### Schema Validators Produce Hard Errors

Schema-backed validators automatically produce `ValidatorOwnership.SCHEMA` violations. These are **hard errors** that cause exit code 1.

The ownership mapping is defined in `packages/skilllint/plugin_validator.py`:

```python
VALIDATOR_OWNERSHIP: dict[str, ValidatorOwnership] = {
    # Schema-backed validators (hard failures)
    "FrontmatterValidator": ValidatorOwnership.SCHEMA,
    "PluginStructureValidator": ValidatorOwnership.SCHEMA,
    "PluginRegistrationValidator": ValidatorOwnership.SCHEMA,
    "HookValidator": ValidatorOwnership.SCHEMA,
    "SymlinkTargetValidator": ValidatorOwnership.SCHEMA,
    # Lint validators (warnings/findings)
    "NameFormatValidator": ValidatorOwnership.LINT,
    "DescriptionValidator": ValidatorOwnership.LINT,
    # ...
}
```

### Testing Schema Changes

Run the frontmatter-related tests:

```bash
uv run pytest packages/skilllint/tests/ -k frontmatter -v
```

---

## Section 2: Adding a Provider Overlay (New Adapter)

Provider adapters encapsulate platform-specific behavior: file patterns, constraint scopes, and validation logic.

### The PlatformAdapter Protocol

All adapters must satisfy the `PlatformAdapter` protocol defined in `packages/skilllint/adapters/protocol.py`:

```python
@runtime_checkable
class PlatformAdapter(Protocol):
    def id(self) -> str:
        """Return the unique platform identifier (e.g. 'claude_code', 'cursor')."""
        ...

    def path_patterns(self) -> list[str]:
        """Return glob patterns matching files this adapter handles."""
        ...

    def applicable_rules(self) -> set[str]:
        """Return the set of rule-series codes this adapter applies (e.g. {'AS', 'CC'})."""
        ...

    def constraint_scopes(self) -> set[str]:
        """Return constraint_scope values from the provider schema."""
        ...

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate the given file path and return violation dicts."""
        ...
```

### Creating a New Adapter

1. **Create the adapter directory**:

```bash
mkdir -p packages/skilllint/adapters/<new_provider>/
```

2. **Implement the adapter class** (see `packages/skilllint/adapters/claude_code/adapter.py` as a template):

```python
# packages/skilllint/adapters/new_provider/adapter.py
from pathlib import Path, PurePath

class NewProviderAdapter:
    def id(self) -> str:
        return "new_provider"

    def path_patterns(self) -> list[str]:
        return [
            "**/.new_provider/**/*.md",
            "**/new-provider.yaml",
        ]

    def applicable_rules(self) -> set[str]:
        return {"AS"}  # AS-series rules apply

    def constraint_scopes(self) -> set[str]:
        # Load from schema or return static set
        return {"shared", "provider_specific"}

    def validate(self, path: Path) -> list[dict]:
        # Platform-specific validation logic
        return []
```

3. **Register via entry points** in `pyproject.toml`:

```toml
[project.entry-points."skilllint.adapters"]
claude_code = "skilllint.adapters.claude_code:ClaudeCodeAdapter"
new_provider = "skilllint.adapters.new_provider:NewProviderAdapter"
```

### How Adapter Discovery Works

The `load_adapters()` function in `packages/skilllint/adapters/registry.py` discovers adapters:

```python
def load_adapters() -> list[PlatformAdapter]:
    eps = importlib.metadata.entry_points(group="skilllint.adapters")
    adapters: list[PlatformAdapter] = []
    for ep in eps:
        adapter_cls = ep.load()
        adapters.append(adapter_cls())
    return adapters
```

Third-party packages can register their own adapters by adding an entry point in their `pyproject.toml` — no modification to skilllint core required.

### Structure-Based Discovery for Provider Directories

When a provider directory lacks a `plugin.json` manifest, skilllint uses structure-based discovery. The `ScanDiscoveryMode` enum in `packages/skilllint/scan_runtime.py` defines three modes:

```python
class ScanDiscoveryMode(StrEnum):
    MANIFEST = "manifest"   # plugin.json explicitly enumerates components
    AUTO = "auto"           # plugin.json exists but omits component arrays
    STRUCTURE = "structure" # provider directories without manifest
```

To add a new provider directory name for structure-based discovery, update `PROVIDER_DIR_NAMES` in `scan_runtime.py`:

```python
PROVIDER_DIR_NAMES: frozenset[str] = frozenset({
    ".claude",
    ".agent",
    ".agents",
    ".gemini",
    ".cursor",
    ".new_provider",  # Add your provider here
})
```

---

## Section 3: Adding a New Lint Rule

Lint rules enforce cross-platform quality standards. They produce `ValidatorOwnership.LINT` violations (warnings that don't fail the build, unless configured otherwise).

### Rule File Location

All lint rules live in `packages/skilllint/rules/`. The file `packages/skilllint/rules/as_series.py` serves as the canonical template.

### Using the @skilllint_rule Decorator

The `@skilllint_rule` decorator registers a function in the global rule registry. From `packages/skilllint/rule_registry.py`:

```python
@skilllint_rule(
    "AS001",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-naming"},
)
def _check_as001(name: str | None) -> dict | None:
    """AS001 — Invalid skill name format.

    Skill names must be lowercase alphanumeric with hyphens only.
    """
    # Validation logic...
```

### Adding to the Ownership Registry

After creating a new lint validator, register it in `packages/skilllint/plugin_validator.py`:

```python
VALIDATOR_OWNERSHIP: dict[str, ValidatorOwnership] = {
    # ... existing entries ...
    "MyNewValidator": ValidatorOwnership.LINT,
}
```

### Adding to the Constraint Scopes Registry

Also register applicable constraint scopes:

```python
VALIDATOR_CONSTRAINT_SCOPES: dict[str, set[str]] = {
    # ... existing entries ...
    "MyNewValidator": {"shared", "provider_specific"},
}
```

### Choosing Severity

Reference the S04 severity classification:

| Severity | When to Use | Exit Code Impact |
|----------|-------------|-------------------|
| `error` | Genuine schema violations, correctness issues | Exit 1 |
| `warning` | Style preferences, best practices, runtime-accepted patterns | Exit 0 |
| `info` | Recommendations, optional improvements | Exit 0 |

**Key principle:** Only use `error` for violations that genuinely break functionality. Use `warning` for style rules and patterns that the runtime accepts but aren't preferred.

### Testing Lint Rules

Run tests filtered by rule code:

```bash
uv run pytest packages/skilllint/tests/ -k as001 -v
uv run pytest packages/skilllint/tests/ -k <rule_code> -v
```

---

## Section 4: Adding Provenance Metadata

Provenance metadata (`authority` dicts) enables traceability from any violation back to its authoritative source. This satisfies requirements D002 and D005 for auditable validation origins.

### Authority Dict Structure

The `authority` dict has a standard shape:

```python
authority = {
    "origin": "agentskills.io",          # Required: the authoritative source
    "reference": "/specification#skill-naming"  # Optional: path/anchor within source
}
```

### In Schema Files

Add a top-level `provenance` key (or per-field `x-audited`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "provenance": {
    "authority_url": "https://docs.anthropic.com/claude-code",
    "last_verified": "2026-03-14",
    "provider_id": "claude_code"
  },
  "file_types": {
    "skill": {
      "fields": {
        "name": {
          "required": true,
          "constraint_scope": "shared",
          "x-audited": {
            "date": "2026-03-10",
            "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md"
          }
        }
      }
    }
  }
}
```

### In Rule Definitions

Pass the `authority` kwarg to `@skilllint_rule`:

```python
@skilllint_rule(
    "AS001",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-naming"},
)
def _check_as001(name: str | None) -> dict | None:
    ...
```

The decorator converts this to a `RuleAuthority` dataclass (defined in `packages/skilllint/rule_registry.py`):

```python
@dataclass
class RuleAuthority:
    origin: str              # e.g., "agent-skills.io", "anthropic.com"
    reference: str | None = None  # URL or doc path
```

### In Violation Dicts

Rules can include authority directly in violation outputs:

```python
def _make_violation(code: str, severity: str, message: str, fix: str | None = None) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "authority": _get_rule_authority(code)  # Looked up from registry
    }
```

### Why It Matters

Provenance metadata enables:

1. **Auditability:** Every violation can be traced to its source specification
2. **Freshness detection:** `last_verified` dates indicate when schema constraints were last checked against the upstream spec
3. **Debugging:** Users can click through to the authoritative documentation
4. **Compliance:** Satisfies D002 (traceability to specs) and D005 (machine-readable provenance)

---

## Quick Reference

| What | Where | Key Pattern |
|------|------|--------------|
| Schema JSON | `packages/skilllint/schemas/<provider>/vN.json` | `file_types.<type>.fields.<field>` |
| Adapter Protocol | `packages/skilllint/adapters/protocol.py` | `PlatformAdapter` Protocol |
| Adapter Registry | `packages/skilllint/adapters/registry.py` | `load_adapters()` via entry_points |
| Rule Registry | `packages/skilllint/rule_registry.py` | `@skilllint_rule` decorator |
| Ownership Mapping | `packages/skilllint/plugin_validator.py` | `VALIDATOR_OWNERSHIP` dict |
| Constraint Scopes | `packages/skilllint/plugin_validator.py` | `VALIDATOR_CONSTRAINT_SCOPES` dict |
| Discovery Modes | `packages/skilllint/scan_runtime.py` | `ScanDiscoveryMode` enum |
| Provider Directories | `packages/skilllint/scan_runtime.py` | `PROVIDER_DIR_NAMES` frozenset |
