---
name: skilllint
description: 'Use the skilllint CLI to validate, explain, and fix agent plugins, skills, agents, commands, and platform files. Use when asked to lint agent artifacts, investigate a skilllint rule ID, or verify a plugin before commit.'
argument-hint: '[rule-id | path]'
---

# skilllint

Use the installed CLI as the source of truth for commands, rules, severity,
platform applicability, fixability, and thresholds. Do not reproduce those
runtime-owned facts from this skill.

Arguments received: `$ARGUMENTS`

## 1. Resolve the invocation

Prefer an already-installed `skilllint` executable.

```bash
skilllint --version
```

When it is unavailable, use the first available package manager.

With `uv`, run the published tool without a permanent installation:

```bash
uvx skilllint@latest --version
```

With `pipx`, run the published tool without a permanent installation:

```bash
pipx run skilllint --version
```

With only `pip`, install the package into the active Python environment, then
use the `skilllint` executable:

```bash
python -m pip install skilllint
skilllint --version
```

When working inside a skilllint source checkout, follow that repository's
development instructions instead of installing a second copy.

Use the same invocation form for the remaining commands.

## 2. Route the request

- A rule ID such as `FM010`: run `skilllint rule <ID>`.
- A supplied path: run `skilllint check --show-summary --show-progress <path>`.
- No argument: scan the user-requested repository scope; when no narrower scope
  is established, use the current working directory.
- A request that names a target platform: add `--platform <platform>` to the
  `check` command. Without it, every matching platform adapter runs. Take the
  accepted platform names from `skilllint check --help`.

If command syntax or available subcommands are uncertain, run
`skilllint --help` or the relevant subcommand's `--help`. Do not rely on a
command inventory copied into this skill.

## 3. Scan and identify findings

Run:

```bash
skilllint check --show-summary --show-progress <path>
```

Collect the rule IDs emitted by the actual scan. Do not infer a rule from a
similar-looking problem when the tool can identify it directly.

For each finding that needs explanation, run:

```bash
skilllint rule <ID>
```

The per-rule output includes the rule's severity, category, and platform
scope.

Use `skilllint rules` to compare current severity and fixability across the
catalog.

## 4. Fix from runtime evidence

For a manual finding, use the remediation returned by `skilllint rule <ID>`.

For findings currently reported as fixable, apply the tool's supported fixer:

```bash
skilllint check --fix <path>
```

Do not assume a rule is fixable because an older copy of this skill said so.
If `--fix` is rejected for the selected invocation, inspect
`skilllint check --help` and use the supported route.

Review the resulting diff before treating an automatic edit as correct.

## 5. Verify

Re-run validation without mutation:

```bash
skilllint check --check --show-summary <path>
```

Report remaining findings by rule ID. A zero exit status establishes the
current scan's exit contract; it does not prove that unrelated paths or
platforms were selected.

When the repository being edited defines additional test, lint, or completion
gates, run those separately before declaring the repository change complete.
