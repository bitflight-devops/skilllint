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

### Full human diagnostics

Use `check --output-format full` for source-aware human reports:

```console
uv run skilllint check --output-format full --color auto plugins/my-plugin
uv run skilllint check --output-format full --color always --record findings.svg plugins/my-plugin
```

Each finding shows severity, rule code, message, actual source path, help, and
rule documentation. Verified source ranges include an excerpt and caret marks.
Columns in the location count Unicode code points; caret positions account for
tabs and terminal display widths. Long lines are cropped around the highlighted
range, and multiline ranges show their first and last affected lines.

The renderer checks that the source still matches the text that produced the
finding. Missing, changed, unreadable, or unverified sources fall back to the
file path without a guessed line, column, or excerpt. Legacy line labels are
not used to invent a location. Control characters are displayed as escapes.

`--color auto|always|never` controls human colour independently of the selected
format. Full defaults to terminal-aware `auto`; `always` also colours redirected
output and `never` disables ANSI. `--no-color` takes precedence. The five machine
formats remain plain regardless of colour settings. Omitting both the format
and colour options preserves the legacy reporter and its defaults.

`--verbose`, `--show-progress`, `--show-summary`, and `--fix` keep their usual
meaning. Full `--record` exports the same human report from the same scan;
machine formats and legacy `--json` retain their existing human sidecars.
Recording preserves the report's styles even when terminal ANSI is disabled.
Exit status remains based on validation results, not visible findings. Explicit
`--output-format` cannot be combined with `--json` or `--tokens-only`.

See the [actual full-colour capture](../examples/output/README.md#full-human-diagnostics).

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

Stdout contains one compact UTF-8 JSON object per line (LF, or CRLF on Windows), with no ANSI
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

### GitHub annotations

Use `check --output-format github` in a GitHub Actions `run` step:

```console
uv run skilllint check --output-format github plugins/my-plugin
```

The CLI emits plain [workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#setting-an-error-message)
which GitHub interprets as annotations. Errors use `error`, warnings use
`warning`, and info findings use `notice` only with `--verbose`. Each annotation
includes its rule code as a title, message, and available suggestion/help.
Properties escape percent signs, CR/LF, colons, and commas according to the
[official Actions toolkit](https://github.com/actions/toolkit/blob/main/packages/core/src/command.ts).
Messages escape percent signs and CR/LF; other controls are shown as visible
escapes so hostile filenames or multiline messages cannot inject commands.
Ordinary diagnostics remain on stderr. In this format, their modern `::` and
legacy `##[` command markers are neutralized so invalid paths and policy
warnings, parser errors, and uncaught command tracebacks cannot masquerade as
runner commands.

Actual source paths take precedence over checked targets. Known one-based
positions are included; legacy field labels and line values are not guessed.
Half-open source ranges become inclusive GitHub end coordinates. Multiline
ranges omit columns, as required by GitHub. A range ending at column one excludes
that final line. Unknown line/column properties are omitted. GitHub itself may
present a file-only annotation at its default line one; that is not a position
reported by skilllint.

Relative source paths are anchored to the current directory before formatting.
The `GITHUB_WORKSPACE` prefix is removed when set, so steps running in a
subdirectory still identify the correct repository file. Without that variable,
the current-directory prefix is removed. Other absolute paths remain absolute,
and paths are never resolved through symlinks.

Commands are sorted and duplicate findings are retained. There are no headings,
progress, fix notices, summaries, or ANSI escapes, even with forced terminal
colour. A clean scan emits nothing. `--fix` applies the existing fixes and
reports remaining findings. Exit codes stay `0` for success, `1` for validation
failure, and `2` for usage errors. Check exit status even when output is empty.
`--json` and `--tokens-only` cannot be combined with `--output-format`.
`--record` remains a detailed human-report sidecar, not the workflow protocol.

See the [real output and labelled SVG preview](../examples/output/README.md#github-annotations).

### GitLab Code Quality

Use `check --output-format gitlab` to produce a
[GitLab Code Quality report](https://docs.gitlab.com/ci/testing/code_quality/#code-quality-report-format):

```console
uv run skilllint check --output-format gitlab plugins/my-plugin > gl-code-quality-report.json
```

Stdout is one BOM-free JSON array containing `description`, `check_name` (rule
code), `fingerprint`, `severity`, and `location.path` / `location.lines.begin`.
The description includes the field, message, and available suggestion/help.
Skilllint errors map to `major`, warnings to `minor`, and verbose info to `info`.
These are presentation mappings, not a change to rule severity or exit status.

Paths are relative to the nearest enclosing `.git` checkout root (including
worktrees). Run from that repository; for a source export without `.git`, run
from its root because the current directory becomes the report root. Actual
source paths take precedence over checked targets. Paths use `/` without `./`.
In-tree symlink spellings are retained; parent traversals are resolved to their
actual file before relativizing, so a symlink plus `..` is not misinterpreted.

GitLab requires a line. Known source starts use their actual one-based line.
For a known file with no source position, line `1` is only a **display anchor**,
and the description explicitly says it is file-level, not a source position.
Legacy line values and semantic field names are never used to invent positions.
Directory/global findings, missing files, and sources outside the repository
(including symlinks to external files) cannot be represented faithfully. Each
is omitted from the array **with its complete finding details on stderr**.
Keep the job log and exit status; use `json-lines` when every finding must be in
one machine-readable artifact. An empty array alone does not prove success.

Fingerprints are SHA-256 hashes of the repository-relative path, validator,
rule, field, message, and duplicate occurrence number. Source coordinates,
severity, and help text do not enter the hash. The structured source path is
repository-relative; text embedded in a message remains part of its identity.
Occurrences are ordered by source position and report content so input iteration order does
not change the result. Identical findings have distinct fingerprints, because
GitLab collapses identical fingerprints. Moving a finding's lines alone keeps
its fingerprint; adding/removing indistinguishable occurrences can reassign
occurrence numbers, and changes to the path or message change identity.

A clean scan emits `[]`. No human headings, progress, fix notices, summaries,
or ANSI escapes appear on stdout. `--fix` reports remaining findings and normal
exit codes remain `0` (pass), `1` (validation failure), and `2` (usage error).
Usage errors leave stdout empty. `--json` and `--tokens-only` are incompatible;
`--record` remains a separate human-rendered SVG/HTML report.

In an existing GitLab job with the repository's environment installed, add:

```yaml
skilllint:
  script:
    - uv run skilllint check --output-format gitlab plugins/my-plugin > gl-code-quality-report.json
  artifacts:
    when: always
    paths:
      - gl-code-quality-report.json
    reports:
      codequality: gl-code-quality-report.json
```

The command retains its failure status; do not append `|| true`. Uploading the
artifact does not require making the job pass. Run the job on the target branch
as well: GitLab needs a target-branch baseline to compare new/resolved findings.
This integration is checked against the published report contract and actual
CLI output, not a live GitLab ingestion test. See the
[raw report and syntax-coloured SVG preview](../examples/output/README.md#gitlab-code-quality).

### JUnit-style XML

Use `check --output-format junit` to export executed validation results:

```console
uv run skilllint check --output-format junit plugins/my-plugin > skilllint-junit.xml
```

This is the JUnit-style `testsuites` / `testsuite` / `testcase` dialect used by
[GitLab unit test reports](https://docs.gitlab.com/ci/testing/unit_test_reports/#junit-xml-format-specification)
and other JUnit consumers. It is **not** the distinct
[xUnit.net XML v2 dialect](https://xunit.net/docs/format-xml-v2), which uses
`assemblies` / `assembly` / `collection` / `test`. There is no `xunit` alias.

One testcase represents one collected target/validator result, including clean
results. It does not claim that every known rule ran. The checked target is the
`classname`; the validator plus a deterministic occurrence suffix is the `name`.
Paths under the current working directory are relative, and other paths are
retained. Duplicate results remain separate with unique classname/name pairs,
including after XML sanitization. Stable sorting makes reordering the same
results produce identical XML; use the same working directory across runs.

A failed validation result produces one `failure` containing all its error
findings, or an explicit explanation if no error diagnostic was supplied.
Warnings and `--verbose` info findings go in that testcase's `system-out` and do
not create failures. The collected pass/fail flag, not diagnostic counts,
controls both the report's failure status and CLI exit status. If a validator
marks a result passed while supplying errors, those diagnostics remain visible
in `system-out` without overriding its status.

Each diagnostic retains severity, code, field, message, source coordinates when
known, suggestion, and help reference. Missing positions are not invented.
Directory, external, and missing-file targets remain representable. XML markup
is escaped; XML 1.0-prohibited characters, including NUL, ESC, and lone
surrogates, become visible Python-style escapes. Valid carriage returns use XML
character references so parsing does not silently normalize them to newlines.
Non-ASCII text also uses character references, preserving its value without
depending on the terminal encoding.

Suite and aggregate `tests`/`failures` counters count actual result testcases;
`errors` and `skipped` are zero because lint failures are validation failures,
not test-runner errors or skipped tests. A scan with no collected results emits
a valid zero-test report. No durations or timestamps are invented.

Stdout contains only XML, regardless of colour, progress, or summary flags.
Usage and policy diagnostics remain on stderr. `--fix` reports the resulting
validation state without a second scan. `--record out.svg` still saves the human
report separately. Exit status remains `0` for passed validation, `1` for failed
validation, and `2` for invalid usage. `--json` and `--tokens-only` conflict with
explicit `--output-format`. Existing formats and GitHub Action outputs are unchanged.

In an existing GitLab job with skilllint installed:

```yaml
skilllint:
  script:
    - uv run skilllint check --output-format junit plugins/my-plugin > skilllint-junit.xml
  artifacts:
    when: always
    paths:
      - skilllint-junit.xml
    reports:
      junit: skilllint-junit.xml
```

Keep the command's exit status; do not add `|| true`. GitLab's report upload does
not itself determine whether a job fails. The report uses GitLab's documented
subset, with diagnostic output inside testcases. Compatibility is checked with
XML parsers and this field contract, not a live CI interface ingestion test.
See the [actual XML and syntax-coloured preview](../examples/output/README.md#junit-style-xml).

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

The Action and package version can be pinned independently. Packages containing
the structured Action runner publish annotations and all existing outputs from
one scan, retaining human rendering options and fix behavior. `inspected-count`
comes from collected results (or token-count entries), and `findings` includes
visible finding codes plus applied-fix codes. An invalid invocation leaves both
empty, as before. Human logs are printed with workflow-command interpretation
suspended; only the explicitly escaped annotations are interpreted.

For older pins without that runner, the Action explicitly announces its legacy
compatibility path. Historical output parsing and possible counting rescans are
preserved there; new native annotations are not guaranteed. Use a package with
the structured runner for the new behavior. `version: source` installs from the
local Git checkout of this repository and is intended for unreleased-source
integration tests with `uses: ./`. The checkout must include Git metadata;
GitHub's downloaded remote Action archive does not include it.


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

Install pre-commit and use Python 3.11–3.14 for the skilllint hook:

```console
python -m pip install pre-commit
```

Add this configuration to `.pre-commit-config.yaml`. Replace `vX.Y.Z` with a
release tag or commit SHA that includes the hooks and output format you need.
The placeholder does not name a published release. Pre-commit installs
skilllint in an isolated hook environment, so a separate skilllint installation
is not needed for this configuration.

```yaml
repos:
  - repo: https://github.com/bitflight-devops/skilllint
    rev: vX.Y.Z
    hooks:
      - id: skilllint
```

Install the Git hook and run the check across matching tracked files:

```console
pre-commit install
pre-commit run skilllint --all-files
```

Subsequent commits check matching staged files. To check selected paths without
making a commit, pass their filenames:

```console
pre-commit run skilllint --files skills/my-skill/SKILL.md
```

`skilllint` checks without mutating files. To apply supported fixes instead,
replace `id: skilllint` with `id: skilllint-fix` in the configuration, then run:

```console
pre-commit run skilllint-fix --all-files
git diff
```

A fix run that changes files stops the commit so you can review and re-stage
the edits. Run it again after review; supported fixes are idempotent. Use the
fix hook rather than adding `--fix` to the check hook's `args`.

Both hooks select `--output-format concise --no-color` by default: one plain
line per remaining finding, with known source coordinates, no ANSI colour,
and no skilllint headings, progress, fix notices, or summary. The hook runner
still prints its own pass/fail and modified-file status. The same file matching
and `failing-examples/` exclusion apply to both hooks.

Append supported CLI arguments with `args: [--verbose]` to include info
findings. The check hook also accepts `args: [--platform, cursor]`; do not use
`--platform` with the fix hook. Add a top-level
`exclude: ^(vendor/|third_party/)` alongside `repos` for additional generated
or vendored paths while retaining the hook's exclusion. A hook-level `exclude`
overrides the supplied hook pattern. The broad by-file-type hook is
intentionally omitted from this guide.

For prek, use the same `.pre-commit-config.yaml` and hook IDs:

```console
uv tool install prek
prek install
prek run skilllint --all-files
```

After selecting the fix hook, the equivalent command is
`prek run skilllint-fix --all-files`. The
[captured concise output and SVG preview](../examples/output/README.md#concise)
show the diagnostics these hooks produce.

## Maintainer checks

From a checkout, run the same gates used by the project:

```console
uv run prek run --all-files
uv run pytest
```

The examples above are source-coupled by
`tests/test_usage_examples.py`; keep commands and their
documented context executable when changing this page.
