# Output examples

## JSON Lines

This **JSONL report preview** adds syntax colour and visual wrapping to the
[raw stdout](json-lines.jsonl) captured from the actual CLI. It is not a terminal
screenshot or a CI interface. Each record remains one physical line in the raw
file; the SVG does not change the report data.

![JSONL report preview with syntax colour and visual wrapping](json-lines.svg)

Run from the repository root:

```console
uv run skilllint check --platform claude-code --output-format json-lines examples/output/fixtures/demo-skill/SKILL.md
```

The [fixture](fixtures/demo-skill/SKILL.md) deliberately contains an invalid name.
The command exits `1` because validation fails. See the
[JSONL contract](../../docs/usage.md#json-lines) for fields and exit semantics.

## Concise

This **concise actual-output preview** renders the [raw stdout](concise.txt)
captured from the CLI. Findings remain monochrome; the coloured frame and label
are presentation only. This is not a platform screenshot or a CI interface.
Visual wrapping keeps the preview readable; each finding remains one physical
line in the raw file.

![Concise actual-output preview with monochrome findings and visual wrapping](concise.svg)

Run from the repository root:

```console
uv run skilllint check --platform claude-code --output-format concise --no-color examples/output/fixtures/demo-skill/SKILL.md
```

The same deliberately invalid fixture exits `1`. Concise output contains only
findings, with no headings, fix suggestions, or summary.

## GitHub annotations

This **GitHub workflow-command preview** renders the [actual CLI stdout](github.txt)
with colour and visual wrapping for readability. It is not a GitHub interface
screenshot. The raw file contains plain workflow commands which GitHub Actions
interprets as error, warning, or notice annotations.

![GitHub workflow-command preview, not a GitHub UI screenshot](github.svg)

Run from the repository root:

```console
uv run skilllint check --platform claude-code --output-format github examples/output/fixtures/demo-skill/SKILL.md
```

The deliberately invalid fixture exits `1`. The command uses the real source
range, includes a suggestion, and percent-escapes embedded newlines. See the
[GitHub annotations contract](../../docs/usage.md#github-annotations).

## GitLab Code Quality

This **GitLab Code Quality report preview** adds syntax colour and visual
wrapping to the [actual CLI JSON report](gitlab.json). It is not a GitLab
interface screenshot, and it does not demonstrate live GitLab ingestion.
The raw file is an unchanged, BOM-free JSON array.

![GitLab Code Quality report preview, not a GitLab UI screenshot](gitlab.svg)

Run from the repository root:

```console
uv run skilllint check --platform claude-code --output-format gitlab examples/output/fixtures/demo-skill/SKILL.md
```

The deliberately invalid fixture exits `1`. See the
[GitLab report contract and CI example](../../docs/usage.md#gitlab-code-quality)
for fingerprint identity, severity mapping, and explicitly disclosed limitations
for findings without a repository file or source position.

## JUnit-style XML

This **JUnit-style XML report preview** adds syntax colour and visual wrapping to
the [actual CLI XML report](junit.xml). It is not a CI interface screenshot or a
live ingestion test. The raw XML remains unchanged; this format is distinct
from xUnit.net's assemblies-based XML dialect.

![JUnit-style XML report preview, not a CI UI screenshot](junit.svg)

Run from the repository root:

```console
uv run skilllint check --platform claude-code --output-format junit examples/output/fixtures/demo-skill/SKILL.md
```

The deliberately invalid fixture exits `1`. Its single collected validator
result becomes one failed testcase, with the full finding and help text. See
[JUnit result semantics and CI configuration](../../docs/usage.md#junit-style-xml).

## Reproduce the examples

Regenerate all artifacts, or verify they match without modifying them:

```console
uv run python scripts/capture_output_examples.py
uv run python scripts/capture_output_examples.py --check
```

The script preserves stdout bytes and uses a fixed SVG identifier and width.
Use the repository's locked dependencies to reproduce the preview.
