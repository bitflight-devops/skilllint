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

## Reproduce the examples

Regenerate all artifacts, or verify they match without modifying them:

```console
uv run python scripts/capture_output_examples.py
uv run python scripts/capture_output_examples.py --check
```

The script preserves stdout bytes and uses a fixed SVG identifier and width.
Use the repository's locked dependencies to reproduce the preview.
