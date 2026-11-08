# Maintainer extension guide

Use this guide to add an adapter, schema constraint, or lint rule. Start with the owning interface and its tests; the [architecture guide](architecture.md) maps the validation pipeline and module responsibilities.

## Choose the seam

| Need | Add | Owner |
| --- | --- | --- |
| provider metadata or fallback validation | `adapters/<provider>/` plus an entry point | `PlatformAdapter` |
| schema-backed shape/type constraint | versioned provider schema | schema validators |
| cross-platform quality rule | `rules/<series>_series.py` and decorator | rule registry + rule emitter |
| traceability for a checkable claim | authority metadata or provenance registry entry | claim locator |

Do not add an adapter for a rule that belongs to the core validator. Do not
declare a rule complete because a decorator, catalog row, or entry point exists;
the public fixture/CLI path must emit the finding.

## Add an adapter

Implement the five-method structural interface in
`packages/skilllint/adapters/protocol.py`:

```python
from pathlib import Path


class ExampleAdapter:
    def id(self) -> str:
        return "example"

    def path_patterns(self) -> list[str]:
        return ["*.json"]

    def applicable_rules(self) -> set[str]:
        return {"EX"}

    def constraint_scopes(self) -> set[str]:
        return {"shared"}

    def validate(self, path: Path) -> list[dict]:
        return (
            [{"code": "EX001", "severity": "error", "message": "example failure"}] if path.name == "fail.json" else []
        )
```

Register the class in the package that owns it:

```toml
[project.entry-points."skilllint.adapters"]
example = "example_skilllint.adapter:ExampleAdapter"
```

`load_adapters()` discovers and instantiates these entry points. The example above is exercised by `packages/skilllint/tests/test_architecture_examples.py`, including building and loading a sample distribution and checking passing/failing CLI results.

Return finding dictionaries with `code`, `severity`, and `message`. Supported diagnostic fields also include `field`, `line`, `suggestion`, `docs_url`, and `source_location`; the core preserves them when converting to `ValidationIssue`. `applicable_rules()` allows rule-series prefixes, while registered rules are also filtered by their platform metadata. Explicit `--platform` validation does not apply fixes.

An adapter that needs to identify plugin roots can also implement the optional `PlatformPluginDiscovery.plugin_layouts()` protocol. It is separate from the five required methods so existing adapters remain compatible. See [adapter discovery](architecture.md#adapters-and-the-extension-seam) for the ownership rules.

## Add a rule

Use `@skilllint_rule` with an explicit code, category, platform, severity, and
authority when an external source supports the claim. The decorator registers
metadata for `skilllint rules` and `skilllint rule CODE`; the check function is
the emitter. Keep registration, emission, severity, validator ownership, and
provenance as separate facts.

Check `uv run skilllint rules` and `uv run skilllint rule CODE` before adding or changing a rule. The registration series includes PR001, PR002, and PR005; their behavior is covered by `test_plugin_registration_validator.py`. PR003, PR004, and SK009 are retired and must not be restored to help, catalog, or examples.

## Schema and provenance

Version schema changes under `packages/skilllint/schemas/<provider>/vN.json`. Preserve `constraint_scope`: `shared` means the core can apply it across providers; `provider_specific` requires the matching adapter.

A provenance claim must identify its rule, authority file/URL and heading (when applicable), extraction shape, assertion locator, expected value, and audit date. `test_provenance_registry_locators.py` resolves Python constants, schema JSON fields, and schema JSON enums and compares them with the recorded expected values. Add coverage for the locator and value used by a new claim.

`scripts/refresh_claim_values.py` currently re-extracts two vendor-backed claims: HK002 event names and HK003 hook types. It updates their registry values and audit metadata when they change; it does not update rule code. `scripts/refresh_schemas.py` versions schema files and preserves constraint scopes. Neither script implements the generalized LLM pipeline described in the [provenance proposal](design-rule-provenance-registry.md).

## Verification checklist

1. Trace required behavior and existing coverage before changing tests. Use
   existing protection when it suffices; add a test only for an uncovered
   requirement or demonstrated regression. Judge runnable examples and
   machine-readable contracts by their observable behavior. Review explanatory
   prose semantically rather than freezing its wording, headings, or source layout.
2. Install/load any retained adapter sample and run both its passing and
   failing public CLI probes with `PYTHONPATH` cleared.
3. Run `uv run skilllint rules` and `uv run skilllint rule CODE`, then exercise the affected public CLI path. For targeted feedback, use `uv run python scripts/run_fast_tests.py packages/skilllint/tests/test_public_rule_emitters.py` or the affected test file, such as `packages/skilllint/tests/test_plugin_registration_validator.py`. The fast profile excludes slow tests and does not replace the full gate.
4. Run `uv run prek run --all-files` and `uv run pytest`.

## Typing boundary

Python 3.11 is the supported baseline. The single enforced type checker is `ty`: the dedicated CI type job checks `packages/`, while the prek hook checks the Python filenames passed to it, including tooling and tests. Run `uv run prek run --all-files` and `uv run pytest` for the full gates. Keep untrusted adapter/file payloads at explicit boundary modules and validate them before passing concrete values inward; see the [typing policy](TYPING_POLICY.md).
