---
name: skilllint
description: 'Use the skilllint CLI to validate, explain, and fix agent plugins, skills, agents, commands, and platform files. Use when asked to lint agent artifacts, investigate a skilllint rule ID, or verify a plugin before commit.'
argument-hint: '[rule-id | path]'
---

# skilllint

Use the installed CLI as the source of truth for commands, rules, severity, platform applicability, fixability, and thresholds.

Arguments received: `$ARGUMENTS`

## 1. Resolve the invocation

Prefer an already-installed executable:

```bash
skilllint --version
```

When it is unavailable, use the first available package manager. With uv or pipx, run the published tool without a permanent installation:

```bash
uvx skilllint@latest --version
pipx run skilllint --version
```

With only pip, install the package into the active Python environment:

```bash
python -m pip install skilllint
skilllint --version
```

When working inside a skilllint source checkout, follow that repository's development instructions instead of installing a second copy. Use the same invocation form for the remaining commands.

## 2. Route the request

- A rule ID such as `FM010`: run `skilllint rule <ID>` and explain the result.
- A supplied path: validate that path.
- No argument: scan the user-requested repository scope; when no narrower scope is established, use the current working directory.
- A named target platform: add `--platform <platform>` to validation commands. Without it, skilllint uses the default compatibility scan. Take the accepted names from `skilllint check --help`.

If command syntax or available subcommands are uncertain, run `skilllint --help` or the relevant subcommand's `--help`.

## 3. Scan and explain findings

Run the check, retaining any requested platform:

```bash
skilllint check --show-summary --show-progress <path>
```

Use the rule IDs emitted by the scan. For each finding that needs explanation, run:

```bash
skilllint rule <ID>
```

The per-rule output includes severity, category, and platform scope.

Use `skilllint rules` to compare current severity and fixability across the catalog.

For machine-readable results, add `--json` to `check`, `rules`, `rule`, or a `docs` command. It produces one compact JSON response on stdout; diagnostics remain on stderr. `check --json` honours `--verbose` and `--show-progress` when listing files, and its `omitted` field identifies results left out of that view. Always check the command's exit status as well as its output.

## 4. Fix from runtime evidence

When fixing findings, use the remediation returned by `skilllint rule <ID>`. For findings currently reported as fixable, apply the supported fixer:

```bash
skilllint check --fix <path>
```

The fix route uses the default compatibility scan and cannot be combined with `--platform`. Keep the requested path scope, review the resulting diff, and use the requested platform again for the verification scan. If the invocation is rejected, inspect `skilllint check --help` before retrying.

## 5. Verify and report

Re-run validation without mutation, retaining any requested platform:

```bash
skilllint check --check --show-summary <path>
```

Report the checked paths, platform selection, applied edits, exit status, and remaining findings by rule ID. Exit `0` means the selected validation passed; it does not establish that unrelated paths or platforms were checked.

When the repository being edited defines additional test, lint, or completion gates, run those separately before declaring the repository change complete.
