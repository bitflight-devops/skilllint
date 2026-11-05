# Usage and integrations

Use skilllint to check skills, agents, commands, plugins, and platform files, then apply supported fixes or send findings to CI. For report fields and serialization details, see the [output format reference](output-formats.md).

## Install

```console
python -m pip install skilllint
skilllint --version
```

Supported Python versions are 3.11–3.15. For an isolated executable, use `uv tool install skilllint`. For a project dependency, use `uv add skilllint` and prefix the commands below with `uv run`, for example `uv run skilllint check skills/`.

## Check, fix, and tokens

Check a plugin directory or an individual skill:

```console
skilllint check --output-format full plugins/my-plugin
skilllint check --output-format full skills/my-skill/SKILL.md
```

Without `--platform`, skilllint selects compatible validators. Limit a scan to one platform when needed:

```console
skilllint check --platform claude-code plugins/my-plugin
skilllint check --platform cursor .cursor/rules
skilllint check --platform codex AGENTS.md
```

`agentskills` names the shared rule taxonomy, not a `check` adapter. To list its rules, use:

```console
skilllint rules --platform agentskills
```

Apply supported fixes in place, then review the changes:

```console
skilllint check --fix plugins/my-plugin
git diff
```

Files are checked again after fixing. Do not combine `--fix` with `--platform`; fixing uses the default compatibility route. A second fix run should make no further changes. Some findings require manual edits; `skilllint rule CODE` explains an individual rule.

To count tokens without running validation:

```console
skilllint check --tokens-only skills/my-skill/SKILL.md
```

Check the exit status in scripts and CI:

- `0`: validation passed. Warnings and info findings may still be present.
- `1`: validation failed.
- `2`: invalid CLI usage or an output-file error, such as an unwritable `--record` destination.

A successful scan covers only the selected files and validators. An empty report alone does not prove success: a validator can fail without supplying a finding. Invalid policy entries produce diagnostics on stderr and use defaults; they do not turn a normal scan into exit `2`.

## Output and selection

Use `--filter` to restrict paths within a directory and `--filter-type` to select `skills`, `agents`, or `commands`. Gitignored paths are skipped unless you add `--include-gitignore`.

```console
skilllint check --no-color --show-progress --show-summary --filter-type skills plugins/my-plugin
skilllint check --include-gitignore generated/SKILL.md
```

For human output, `--show-progress` adds per-file status and `--show-summary` adds final counts. Summary file counts describe selection, not adapter coverage. Use `--verbose` to include info findings.

Choose a report for its destination:

| Destination | Option | Details |
| --- | --- | --- |
| Local investigation | `--output-format full` | [Source excerpts and fixes](#full-human-diagnostics) |
| Pre-commit or plain logs | `--output-format concise` | [One finding per line](#concise) |
| Scripts and agents | `--output-format json-lines` | [JSON Lines](#json-lines) |
| GitHub Actions | `--output-format github` | [Annotations](#github-annotations) |
| GitLab Code Quality | `--output-format gitlab` | [Code Quality setup](#gitlab-code-quality) |
| Test-report consumers | `--output-format junit` | [JUnit setup](#junit-style-xml) |

Omit `--output-format` for the default human report. Use `--json` for a single JSON response from `check`, `rules`, `rule`, or a `docs` command. At the root, it is supported with `--version`. `--json` and `--tokens-only` cannot be combined with `--output-format`.

```console
skilllint check --json plugins/my-plugin
skilllint rule FM007 --json
skilllint --version --json
```

### Full human diagnostics

```console
skilllint check --output-format full plugins/my-plugin
skilllint check --output-format full --record findings.svg plugins/my-plugin
```

Full output shows each finding with its rule, help, and a source excerpt when a verified location is available. Missing or changed source files are shown without guessed coordinates. Colour is detected automatically; use `--color always` to force it or `--color never` (also `--no-color`) to disable it. `--record` saves an SVG or HTML report.

See the [full output reference](output-formats.md#full-human-diagnostics) and [example report](../examples/output/README.md#full-human-diagnostics).

### Concise

```console
skilllint check --output-format concise --no-color plugins/my-plugin
```

Concise output gives one plain line per finding, with source coordinates when known. It has no headings, progress, or summary. Both pre-commit hooks select this format by default. See the [concise reference](output-formats.md#concise) and [example output](../examples/output/README.md#concise).

### JSON Lines

```console
skilllint check --output-format json-lines plugins/my-plugin > findings.jsonl
```

JSON Lines writes one object per finding after the scan finishes. A clean scan produces an empty file. Use it when every visible finding must be available in a machine-readable artifact, including findings that GitLab Code Quality cannot represent. See the [JSON Lines schema](output-formats.md#json-lines) and [example output](../examples/output/README.md#json-lines).

## Rules, thresholds, and severity

Use `skilllint rules` to list rules and `skilllint rule FM007` to read one rule's explanation, default severity, and fixability.

Place a `.skilllint.json` file above the files you want to configure:

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

Configuration discovery walks upward from each checked file's directory, or from a checked directory itself. The first ancestor with a `.skilllint.json` or `.claude-plugin/plugin.json` wins. At a plugin root, `.claude-plugin/validator.json` supplies the configuration instead of `.skilllint.json`, even if `validator.json` is absent. A nearer nested `.skilllint.json` takes precedence over that plugin root. Configurations do not merge.

- `ignore`: rule codes to suppress, keyed by path prefixes relative to the configuration root. An empty prefix applies below the whole root. `skills/legacy` matches that path and its descendants, but not `skills/legacy-old`.
- `thresholds`: positive integer token limits for `SK006` and `SK007`. `SK006` must be below `SK007`; otherwise both revert to defaults.
- `severity`: overrides for `SK006`, `SK007`, and `PL006`, accepting `warning` or `info`.

Unsupported or invalid threshold and severity entries are diagnosed on stderr and defaults are used. Fix the configuration rather than relying on a fallback.

## GitHub Action

Replace `X.Y.Z` with the release you intend to pin. The Action ref and the `version` input independently select the Action code and installed skilllint package.

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

The Action provides `result` (`passed` or `failed`) and `exit-code` (`0`, `1`, or `2`). To let later steps run after a validation failure, use `continue-on-error` and inspect the outputs:

```yaml
- uses: bitflight-devops/skilllint@vX.Y.Z
  id: lint
  continue-on-error: true
  with:
    paths: "plugins/"
    version: "X.Y.Z"
- run: echo "skilllint result=${{ steps.lint.outputs.result }} exit=${{ steps.lint.outputs.exit-code }}"
```

Packages with the structured Action runner generate annotations and outputs from one scan, including when fixing. `inspected-count` counts collected file results or token-count entries; `findings` includes visible finding codes and applied-fix codes. Invalid invocations leave these outputs empty. Human logs are printed with workflow-command interpretation suspended; only escaped annotations are interpreted.

Older package pins use an announced compatibility path that may repeat a scan and does not guarantee native annotations. `version: source` is for testing unreleased code with `uses: ./` in a local checkout of this repository, including its Git metadata. It does not work from GitHub's downloaded remote Action archive.

See the [Action inputs and outputs](../README.md#full-input-reference) for the complete input reference.

### GitHub annotations

For direct CLI use in an existing GitHub Actions job with skilllint installed:

```yaml
- run: skilllint check --output-format github plugins/my-plugin
```

Errors and warnings become annotations; `--verbose` also includes info notices. GitHub receives actual source positions when available. See the [annotation reference](output-formats.md#github-annotations) and [example commands](../examples/output/README.md#github-annotations).

## GitLab CI reports

These examples assume an existing GitLab job with skilllint installed. Keep the command's failure status rather than adding `|| true`. `artifacts: when: always` uploads reports even when validation fails.

### GitLab Code Quality

```yaml
skilllint:
  script:
    - skilllint check --output-format gitlab plugins/my-plugin > gl-code-quality-report.json
  artifacts:
    when: always
    paths:
      - gl-code-quality-report.json
    reports:
      codequality: gl-code-quality-report.json
```

Run the job on the target branch too, so GitLab has a baseline for comparing new and resolved findings. The report requires repository-relative file paths and a line. File-level findings use line 1 as a display anchor, not a reported source position. Findings for directories, missing files, or sources outside the repository are omitted from the array and printed in full on stderr. Keep the job log and exit status; use JSON Lines if you need every finding in one structured artifact.

See the [Code Quality reference](output-formats.md#gitlab-code-quality) and [example report](../examples/output/README.md#gitlab-code-quality).

### JUnit-style XML

```yaml
skilllint:
  script:
    - skilllint check --output-format junit plugins/my-plugin > skilllint-junit.xml
  artifacts:
    when: always
    paths:
      - skilllint-junit.xml
    reports:
      junit: skilllint-junit.xml
```

The report contains one testcase per checked target/validator result, including clean results. Validation failures become test failures; warnings and info do not. These counts describe validation results, not individual rules or rule coverage. This is JUnit-style XML, not the xUnit.net XML v2 dialect.

See the [JUnit reference](output-formats.md#junit-style-xml) and [example report](../examples/output/README.md#junit-style-xml).

## Pre-commit

Install pre-commit and use Python 3.11–3.15 for the skilllint hook:

```console
python -m pip install pre-commit
```

Add this configuration to `.pre-commit-config.yaml`. Replace `vX.Y.Z` with a release tag or commit SHA that includes the hooks and output format you need. The placeholder does not name a published release. Pre-commit installs skilllint in an isolated hook environment, so a separate skilllint installation is not needed for this configuration.

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

Subsequent commits check matching staged files. To check selected paths without making a commit, pass their filenames:

```console
pre-commit run skilllint --files skills/my-skill/SKILL.md
```

`skilllint` checks without mutating files. To apply supported fixes instead, replace `id: skilllint` with `id: skilllint-fix` in the configuration, then run:

```console
pre-commit run skilllint-fix --all-files
git diff
```

A fix run that changes files stops the commit so you can review and re-stage the edits. Run it again after review; supported fixes are idempotent. Use the fix hook rather than adding `--fix` to the check hook's `args`.

Both hooks select `--output-format concise --no-color` by default: one plain line per remaining finding, with known source coordinates, no ANSI colour, and no skilllint headings, progress, fix notices, or summary. The hook runner still prints its own pass/fail and modified-file status. The same file matching and `failing-examples/` exclusion apply to both hooks.

Append supported CLI arguments with `args: [--verbose]` to include info findings. The check hook also accepts `args: [--platform, cursor]`; do not use `--platform` with the fix hook. Add a top-level `exclude: ^(vendor/|third_party/)` alongside `repos` for additional generated or vendored paths while retaining the hook's exclusion. A hook-level `exclude` overrides the supplied hook pattern.

For prek, use the same `.pre-commit-config.yaml` and hook IDs:

```console
uv tool install prek
prek install
prek run skilllint --all-files
```

After selecting the fix hook, the equivalent command is `prek run skilllint-fix --all-files`. The [captured concise output and SVG preview](../examples/output/README.md#concise) show the diagnostics these hooks produce.


## Contributing

For development setup and repository checks, see [AGENTS.md](../AGENTS.md#verifying-a-change) and the [maintainer extension guide](maintainer-extension-guide.md).
