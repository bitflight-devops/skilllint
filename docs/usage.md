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
coverage proof: a zero exit means no remaining error-severity findings, not that
every adapter or file was selected.

```console
uv run skilllint check --fix plugins/my-plugin
uv run skilllint check --tokens-only skills/my-skill/SKILL.md
```

Do not combine `--fix` with `--platform`; fixing always uses the default
compatibility route. A second `--fix` run should make no further changes.

Exit status is stable for scripts and CI: `0` means no error-severity findings
(warnings and info findings may still be printed), `1` means an
error-severity validation finding,
and `2` means invalid CLI usage. Invalid policy entries are diagnosed on
stderr and the documented defaults are used; they do not turn a normal scan
into exit `2`. File counts in the summary describe files selected, not adapter
coverage.

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

Add `--json` to `check`, `rules`, `rule`, or any `docs` command for
machine-readable output: one compact JSON line on stdout, with no colour or
layout, whatever the terminal. Every response names its `command`. Exit status
keeps its meaning: `0` and `1` are results and always print JSON (including
`docs` outcomes such as `not_found`), while invalid usage still exits `2` with a
plain message on stderr and an empty stdout. Diagnostics, such as the policy
warnings described above, stay on stderr. `check --json` lists files by the same
rule `--verbose` and `--show-progress` set for the text output, and reports what
it left out in `omitted`; `--no-color` and `--show-summary` have no effect on it.
`docs sections`, `docs section` and `docs verify` also report `file_exists`, the
only way to tell a missing file from an empty one: the text output treats both
the same. With `--record`, the file is written first and the JSON then carries its
absolute, resolved path as `record_path`. At the root, `--json` is valid only
with `--version`; give it after the command name otherwise.

One visible change reaches the default output: for a mistyped option, Click's
close-match hint can now name it, as in `No such option: --jsn (Possible
options: --json)`. The exit status is still `2`.

```console
uv run skilllint check --json plugins/my-plugin
uv run skilllint rule FM007 --json
uv run skilllint --version --json
```

### Concise

Use `check --output-format concise --no-color` for lightweight pre-commit output:

```console
uv run skilllint check --output-format concise --no-color plugins/my-plugin
```

Each visible finding occupies one physical line:
`path:line:column: severity[CODE] field: message`. The actual source path and
one-based start position are used when known. Otherwise the checked target is
shown, with no invented line or column. The semantic field is omitted when empty.
Absolute paths beneath the working directory become relative; other path
spellings retain their identity without resolving symlinks.

Concise output is always monochrome, including without `--no-color`. Control
characters and line separators are escaped, while readable Unicode is retained.
Lines are sorted lexicographically and duplicates are preserved. Info findings
require `--verbose`. There are no headings, fix notices, progress, or summaries,
even with `--show-progress` or `--show-summary`. A clean scan emits no bytes.

`--fix` still applies the same supported changes and reports remaining findings;
pre-commit itself reports modified files. Exit status remains `0` for success,
`1` for failed validation, and `2` for invalid usage. An empty output does not
prove success if a validator failed without a finding. Usage and policy
diagnostics remain on stderr. `--json` and `--tokens-only` conflict with explicit
`--output-format`; legacy human output and `--json` remain unchanged.
With `--record`, the sidecar remains the existing detailed human report rather
than a capture of concise stdout.

Both published pre-commit hooks select concise output by default. See the
[raw capture and monochrome SVG preview](../examples/output/README.md#concise).

### JSON Lines

Use `check --output-format json-lines` for a flat stream of findings:

```console
uv run skilllint check --output-format json-lines plugins/my-plugin
```

Stdout contains one compact JSON object per line (LF, or CRLF on Windows), with no ANSI
colour, progress, summary, or envelope. `--show-progress` and `--show-summary`
never add text to this stream. Info findings require `--verbose`, just as in
human output. Records are ordered lexicographically by their serialized JSON;
duplicate findings are retained. They are emitted after the scan completes,
not streamed during validation. A clean scan emits no bytes.

Every record has `schema_version: 1`, `path`, `validator`, `code`, `severity`,
`message`, and `field`. Optional `suggestion`, `docs_url`, and `source_location`
are omitted when unavailable, rather than emitted as null. `path` identifies
the checked target; `source_location.path` identifies the actual source file,
which can differ from the checked target. Absolute paths beneath the working
directory become relative. Already-relative paths retain their spelling,
including `..`; absolute external paths remain absolute, including paths on
a different Windows drive. Path normalization does not resolve symlinks.
A known span includes `start` and `end` objects with one-based `line` and
`column`. Columns count Unicode code points, with each tab counting as one;
the end position is exclusive. A point has `start` without `end`, and a
file-only location has just `path`.
Unknown locations are omitted, and legacy coordinates are not invented.
`docs_url` preserves the diagnostic help reference, which can be a URL or a
command such as `skilllint rule FM010`.

`schema_version` increments for breaking field or semantic changes. Consumers
should tolerate unknown additive fields under the same schema version.

Check the process exit status as well as the stream: validation success exits
`0`, failure exits `1`, and invalid CLI usage exits `2`. A validator can fail
without supplying a finding, so an empty stream alone does not prove success.
Diagnostics stay on stderr. `--json` retains the existing envelope format;
`--json` and `--tokens-only` cannot be combined with explicit `--output-format`.
With `--record`, the sidecar remains a human-rendered report, not JSONL.

See the [captured raw output and colour SVG preview](../examples/output/README.md).

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
`skills/legacy-old`. Invalid `thresholds` and `severity` values are diagnosed
and the documented defaults are used; fix the config rather than relying on a
fallback.

## GitHub Action

Pin the Action ref and the package version independently. Replace `X.Y.Z` in the examples with the release you intend to pin. The Action exposes
`result` (`passed` or `failed`) and `exit-code` (`0`, `1`, or `2`).

```yaml
- uses: bitflight-devops/skilllint@vX.Y.Z
  id: skilllint
  with:
    paths: "plugins/"
    version: "X.Y.Z"
    platform: "claude-code"
    show-summary: "true"
    no-color: "true"
```

To observe a failure without blocking a later step, use
`continue-on-error: true` and inspect both outputs:

```yaml
- uses: bitflight-devops/skilllint@vX.Y.Z
  id: lint
  continue-on-error: true
  with:
    paths: "plugins/"
    version: "X.Y.Z"
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
trees. The broad by-file-type hook is intentionally omitted from this guide.

## Maintainer checks

From a checkout, run the same gates used by the project:

```console
uv run prek run --all-files
uv run pytest
```

The examples above are source-coupled by
`tests/test_usage_examples.py`; keep commands and their
documented context executable when changing this page.
