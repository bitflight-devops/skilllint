# Maintainer extension guide

This guide describes the current extension seams. Read the interface and its
tests before adding an adapter, schema claim, or rule.

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

`load_adapters()` discovers and instantiates these entry points. A tiny sample
distribution is retained in the architecture example test so installation,
loading, and one passing/failing CLI result remain executable. Keep third-party
validation output to dictionaries with `code`, `severity`, and `message`; the
core converts them to `ValidationIssue` objects. The core still owns severity
semantics, fixing, revalidation, and reporting.

## Add a rule

Use `@skilllint_rule` with an explicit code, category, platform, severity, and
authority when an external source supports the claim. The decorator registers
metadata for `skilllint rules` and `skilllint rule CODE`; the check function is
the emitter. Keep registration, emission, severity, validator ownership, and
provenance as separate facts.

Current registration rules include PR001, PR002, and PR005. PR001 is a warning
for replacing unregistered agents/commands, not for additive skills. PR002 is
skilllint's error for a registered component whose accepted file/directory/root
target is absent. PR005 is a valid configuration with an optional informational
recommendation when a command path is a skill directory. PR003, PR004, and
SK009 are retired and must not be restored to help, catalog, or examples.

## Schema and provenance

Version schema changes under `packages/skilllint/schemas/<provider>/vN.json`.
Preserve `constraint_scope`: `shared` means the core can apply it across
providers; `provider_specific` requires the matching adapter. The old
`docs/registry-schema-examples.md` remains a companion reference and is not
deleted or treated as a second catalog.

A provenance claim must identify its rule, authority file/URL and heading (when
applicable), extraction shape, assertion locator, expected value, and audit
date. The current locator test proves the supported Python-constant locators;
schema JSON field/enum locators have separate schema validation coverage and
must not be inferred from that test alone. The current refresher has two claims:
the source changed, and the extracted claim matches the maintained value. #146
is the schema-locator and refresh-outcome boundary. Future LLM or generalized
provenance stages are proposed design, not shipped behavior.

## Verification checklist

1. Add a source-coupled test for every documented symbol, heading, and code
   block. Missing source or heading must fail.
2. Install/load any retained adapter sample and run both its passing and
   failing public CLI probes with `PYTHONPATH` cleared.
3. Run `skilllint rules` and `skilllint rule CODE`; use Todo 15 emitter evidence
   for the eight retained stub-backed claims and Todo 14 public-route evidence
   for PR001, PR002, and PR005.
4. Run `uv run prek run --all-files` and `uv run pytest`.

## Typing boundary

Python 3.11 is the supported baseline. The repository's single enforced type
checker is `ty`; its scope is `packages/` (`uv run ty check packages/`). The
repository gates are broader: `uv run prek run --all-files` also runs formatting,
lint, shell, Markdown, and workflow checks, while `uv run pytest` runs tests.
Keep untrusted adapter/file payloads at explicit boundary modules and validate
them before passing concrete values inward; see [TYPING_POLICY.md](TYPING_POLICY.md).
