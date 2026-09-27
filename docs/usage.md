# Usage and integrations

`skilllint` checks agent skills, agents, commands, plugins, and platform files.
This page is the canonical guide for installation, the CLI, configuration,
GitHub Actions, and pre-commit.

## Install

```console
python -m pip install skilllint
skilllint --version
```

For an isolated executable, use `uv tool install skilllint`; for a project
dependency use `uv add skilllint`. Supported Python versions are 3.11–3.14.

## Check, fix, and tokens

The default route scans the supplied paths using the compatible validators.
Platform selection is explicit when a scan must be limited:

```console
uv run skilllint check --no-color --show-summary plugins/my-plugin
uv run skilllint check --platform claude-code plugins/my-plugin
uv run skilllint check --platform cursor .cursor/rules
uv run skilllint check --platform codex AGENTS.md
```

`--platform agentskills` is not a `check` namespace. Use the concrete adapter
for a check; `agentskills` is the shared rule taxonomy used by `rules`:

```console
uv run skilllint rules --platform agentskills
```

Fixes are applied in place and the files are checked again. Fixing is not
coverage proof: a zero exit means no remaining reported violations, not that
every adapter or file was selected.

```console
uv run skilllint check --fix plugins/my-plugin
uv run skilllint check --tokens-only skills/my-skill/SKILL.md
```

Do not combine `--fix` with `--platform`; fixing always uses the default
compatibility route. A second `--fix` run should make no further changes.

Exit status is stable for scripts and CI: `0` means no reported violations,
`1` means validation findings, and `2` means invalid usage or configuration.
Warnings and info findings are reported separately from errors; file counts in
the summary describe files selected, not adapter coverage.

## Output and selection

Use `--no-color` for logs, `--verbose` for info findings, `--show-progress` for
per-file status, and `--show-summary` for the final counts. `--filter` limits
paths within a directory and `--filter-type` accepts `skills`, `agents`, or
`commands`. Gitignored paths are skipped by default; add
`--include-gitignore` when those files are intentionally in scope.

```console
$ uv run skilllint check --no-color --show-progress --show-summary \
    --filter-type skills plugins/my-plugin
$ uv run skilllint check --include-gitignore generated/SKILL.md
```

## Rules, thresholds, and severity

`skilllint rules` is the compact catalog; `skilllint rule FM007` explains one
rule. The optional `.skilllint.json` config is discovered from the file's
directory upward. Inside a plugin, `.claude-plugin/validator.json` takes
priority. Configurations do not merge: the nearest applicable file wins.

```json
{
  "ignore": {
    "": ["AS008"],
    "skills/legacy": ["FM007"]
  },
  "thresholds": {"SK006": 4400, "SK007": 8800},
  "severity": {"SK006": "warning"}
}
```

Ignore keys are path prefixes relative to their config root. An empty prefix
matches every file below it; `skills/legacy` does not match a sibling such as
`skills/legacy-old`. Invalid policy values are rejected with diagnostics and
the documented defaults are used; fix the config rather than relying on a
fallback. See [`ignore-config.md`](ignore-config.md) for the complete ignore
reference.

## GitHub Action

Pin the Action ref and the package version independently. The Action exposes
`result` (`passed` or `failed`) and `exit-code` (`0`, `1`, or `2`).

```yaml
- uses: bitflight-devops/skilllint@v1.7.0
  id: skilllint
  with:
    paths: "plugins/"
    version: "1.7.0"
    platform: "claude-code"
    show-summary: "true"
    no-color: "true"
```

To observe a failure without blocking a later step, use
`continue-on-error: true` and inspect both outputs:

```yaml
- uses: bitflight-devops/skilllint@v1.7.0
  id: lint
  continue-on-error: true
  with:
    paths: "plugins/"
- run: echo "skilllint result=${{ steps.lint.outputs.result }} exit=${{ steps.lint.outputs.exit-code }}"
```

## Pre-commit

The retained hooks run on staged files. Pin a release (or commit SHA), and
append supported CLI arguments under `args`:

```yaml
repos:
  - repo: https://github.com/bitflight-devops/skilllint
    rev: v1.7.0
    hooks:
      - id: skilllint
      - id: skilllint-fix
```

`skilllint` checks without mutating files; `skilllint-fix` applies supported
fixes and is idempotent. Use the hook's `exclude` for generated or vendored
trees. The broad by-file-type hook remains available for non-standard layouts
but is intentionally not a canonical recommendation.

## Maintainer checks

From a checkout, run the same gates used by the project:

```console
uv run prek run --all-files
uv run pytest
```

The examples above are source-coupled by
`packages/skilllint/tests/test_usage_examples.py`; keep commands and their
documented context executable when changing this page.
