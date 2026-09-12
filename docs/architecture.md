# Current architecture

`skilllint` is a command-line validation pipeline. The public seam is the
`skilllint check` command; the implementation is split into discovery,
validation, rule registration, fixing, and reporting modules.

## Runtime flow

```text
CLI (plugin_validator.main)
  -> scan_runtime._resolve_filter_and_expand_paths
  -> scan_runtime._discover_validatable_paths
  -> plugin_validator.validate_file / validate_single_path
  -> schema validators and registered rules
  -> optional fixer, then revalidation
  -> reporting.ConsoleReporter or CIReporter
```

`scan_runtime.detect_scan_context` classifies a directory as manifest, auto,
structure, or bare. `_discover_validatable_paths` dispatches that classification
to `_discover_plugin_paths` and the other discovery implementations. Omitting
`--platform` preserves the default compatibility route.
An explicit platform selects a registered `PlatformAdapter`; explicit-platform
validation is validation-only and does not apply fixes. Discovery selects
paths; an adapter does not replace the core validators.

## Adapters and the extension seam

`PlatformAdapter` in `packages/skilllint/adapters/protocol.py` is a structural
interface with `id`, `path_patterns`, `applicable_rules`, `constraint_scopes`,
and `validate`. `adapters.registry.load_adapters()` loads entry points from
the `skilllint.adapters` group and instantiates them. A third-party adapter is
therefore an adapter at this seam, not a change to the core validator.

Adapters provide platform metadata and platform-specific fallback validation.
For third-party adapters, non-`SKILL.md` files use the adapter's
`validate(path)` route directly and do not run core validators; the bundled
Claude adapter is the limited exception that enters the existing core pipeline
for recognized paths. Adapters assign severity on finding dictionaries; the
core interprets it into `ValidationResult`, applies fixer authorization, and
owns reporter output. Adapter metadata or registration does not prove that a
rule emits a finding: public fixture/CLI evidence is emitter proof.

## Rules, ownership, severity, and provenance

The `@skilllint_rule` decorator in `rule_registry.py` registers documentation,
category, platform, severity, fixability, and optional authority metadata.
`ValidatorOwnership` in `plugin_validator.py` records whether a validator is
schema-backed or lint-owned. These are separate dimensions: ownership does
not wire severity, and registry membership does not create an emitter.

`skilllint rules` renders the active registry. `skilllint rule CODE` renders a
single registered rule. PR001, PR002, and PR005 are active public-route rules:
PR001 warns only for unregistered agents/commands (not additive skills), PR002
reports an error for missing registered component targets using accepted file,
directory, root, and `./` shapes, and PR005 is an informational recommendation
for a command path that is also a skill directory. PR003, PR004, and SK009 are
retired and must not appear in the active catalog/help.

The maintained provenance chain is rule claim -> authority -> recorded
extraction/locator -> comparison. The refresher currently has two claims: the
fetched source changed, and the extracted claim matches the maintained value.
A future LLM/general provenance pipeline is proposed only; it is not shipped.

## Fixing and reporting

`scan_runtime.run_validation_loop` orchestrates file iteration and sends
resulting `FileResults` to the selected reporter. The
`plugin_validator.validate_single_path` function owns per-path validation,
fixer authorization, revalidation, and
the distinction between a fixer and its reporting rule. Exit status is derived
from resulting errors and usage/validation contracts, not adapter registration.

## Maintainer map

| Concern | Maintained seam | Proof |
| --- | --- | --- |
| path selection | `scan_runtime.py` | scan runtime tests |
| platform metadata | `adapters/protocol.py`, `adapters/registry.py` | adapter protocol tests |
| schema constraints | `schemas/`, schema validators | schema/frontmatter tests |
| lint rules | `rules/`, `rule_registry.py` | rule fixture and CLI tests |
| fix authorization | `plugin_validator.py` trigger map | fixer/revalidation tests |
| output | `reporting.py` | reporter/CLI tests |

The versioned Claude runtime contract remains evidence for the version named
by its filename; it is not rewritten by this guide. Historical issue states are
recorded as follows: #112 closes only at its accepted PR #187 boundary, #124
remains the registration/emitter boundary until both proofs land, and #146
supplies the schema locator and refresh outcomes. None implies a general
enrollment system.
