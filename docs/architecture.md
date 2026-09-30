# Current architecture

`skilllint` is a command-line validation pipeline. The public seam is the
`skilllint check` command; the implementation is split into discovery,
validation, rule registration, fixing, and reporting modules. Dependency-light
validation contracts (`ValidationIssue`, `ValidationResult`, `AppliedFix`, the
validator protocol, and shared value aliases) are owned by `models.py`.
`policy.py` owns configuration discovery, threshold/severity policy, and suppression filtering.
`frontmatter_yaml.py` owns dependency-light YAML parsing and round-trip repair primitives shared by validation and rules.
`fixing.py` owns fail-closed fixer authorization and generic ordered execution.
`plugin_validator.py` re-exports model, policy, and fixing names for compatibility while its
remaining responsibilities are decomposed incrementally under #283.

## Runtime flow

```text
CLI (plugin_validator.main)
  -> scan_runtime._resolve_filter_and_expand_paths
  -> scan_runtime._discover_validatable_paths
  -> plugin_validator.validate_file / validate_single_path
  -> policy._resolve_policy / _resolve_ignore_config
  -> schema validators and registered rules
  -> fixing.apply_authorized_fixes
  -> optional revalidation
  -> reporting.ConsoleReporter or CIReporter
```

`scan_runtime.detect_scan_context` classifies a directory as `PLUGIN`, `PROVIDER`,
or `BARE`. `_discover_validatable_paths` dispatches that classification to
`_discover_plugin_paths` and the other discovery implementations, whose
downstream logic selects manifest, auto, or structure discovery modes. Omitting
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
Under `--platform`, every adapter uses the same routing contract:
`applicable_rules()` is the coarse allow-list of rule-series prefixes, and
`RuleEntry.platforms` narrows registered rules within those series.
`platforms=["agentskills"]` is platform-neutral; a named platform applies
only to that adapter. `ALL_RULE_SERIES` means every registered series whose
rule metadata applies to the adapter. Claude Code declares that sentinel rather
than copying the current validator implementation into adapter metadata. Codex
declares `AS/CX/FM/SK/LK`; Cursor declares `AS/CU/FM/SK/LK`. Both
adapter-native findings and findings from the core validator pipeline pass
through this same contract. AS runs once per `SKILL.md` before nested core
results are collected.

Explicit directory discovery has a separate optional extension seam:
`PlatformPluginDiscovery.plugin_layouts()`. A layout identifies a manifest
relative to its plugin root and, when needed, the validation target represented
by that manifest. The bundled roots are Claude Code
`.claude-plugin/plugin.json`, portable Agent Plugins `plugin.json` for
Codex and Cursor, Codex compatibility `.codex-plugin/plugin.json`, and Cursor
compatibility `.cursor-plugin/plugin.json`. Once a marked plugin root is
identified, another platform's broad path pattern cannot claim files inside it
unless that adapter also declares the same root layout. A third-party adapter
can opt into the same ownership model without a core type check. Directly
supplied files retain the existing explicit-file behavior.

The adapter boundary remains dictionary-shaped for compatibility, but
conversion preserves diagnostic identity (`field`, `line`, `suggestion`,
and `docs_url`) before reporter output. Adapters assign severity on finding
dictionaries; the core interprets it into `ValidationResult`, applies fixer
authorization on the non-platform fixing path, and owns reporter output.
Adapter metadata or registration does not prove that a rule emits a finding:
public fixture/CLI evidence is emitter proof.

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

`fixing.py` owns the rule-to-fixer authorization map and the generic execution
coordinator. It receives an already ordered fixer sequence and pre-suppression
finding codes, fails closed for undeclared fixers, records `AppliedFix`
instances, and tells its caller whether revalidation is required. It does not
select concrete validators or own mutation implementations.

`frontmatter_yaml.py` now supplies syntax-level parsing and repair primitives without importing validators or rules.
`FrontmatterValidator` still owns schema-aware frontmatter mutation orchestration; this keeps the YAML owner
below rule and validation dispatch rather than creating a reverse dependency.

`plugin_validator._get_fixers_for_path` still owns fixer selection and ordering
for this migration slice, while `plugin_validator.validate_single_path` owns
per-path validation and revalidation. `scan_runtime.run_validation_loop`
orchestrates file iteration and sends resulting `FileResults` to the selected
reporter. Exit status is derived from resulting errors and usage/validation
contracts, not adapter registration.

## Maintainer map

| Concern | Maintained seam | Proof |
| --- | --- | --- |
| validation contracts | `models.py` | model/compatibility contract tests |
| policy/config/suppression | `policy.py` | policy/config discovery and compatibility tests |
| path selection | `scan_runtime.py` | scan runtime tests |
| platform metadata | `adapters/protocol.py`, `adapters/registry.py` | adapter protocol tests |
| schema constraints | `schemas/`, schema validators | schema/frontmatter tests |
| frontmatter YAML parsing/repair | `frontmatter_yaml.py` | frontmatter and rule-deduplication tests |
| lint rules | `rules/`, `rule_registry.py` | rule fixture and CLI tests |
| fix authorization/execution | `fixing.py` | fixer-gating and compatibility tests |
| fix selection/revalidation | `plugin_validator.py` | fixer ordering/revalidation tests |
| output | `reporting.py` | reporter/CLI tests |

The versioned Claude runtime contract remains evidence for the version named
by its filename; it is not rewritten by this guide. Historical issue states are
recorded as follows: #112 closes only at its accepted PR #187 boundary, #124
remains the registration/emitter boundary until both proofs land, and #146
supplies the schema locator and refresh outcomes. None implies a general
enrollment system.
