# Claude Code filesystem-agent `skills` contract (2.1.251)

This record captures the version-specific runtime evidence behind `AG003` and
`normalize_agent_skills_value`. The public subagent documentation defines the
field and shows its canonical YAML-list form, but it does not define every raw
frontmatter shape accepted by the filesystem loader. Those details were
verified against Anthropic's published Claude Code package.

## Audited artifacts

Audit date: 2026-08-30

| Artifact | SHA-256 |
|---|---|
| `@anthropic-ai/claude-code@2.1.251` npm tarball | `44d28caf1711767c14a0388db56b13f49dbd8d3e1db635dd98aa3115c760cf27` |
| `@anthropic-ai/claude-code-linux-x64@2.1.251` npm tarball | `7e2d6d13baccd64cd2d9a8781643ae23a48db009ad746d1df0cfec38d5ed0a44` |
| Extracted Linux x64 `claude` binary | `fd5f10ff0eb58daec04900466b143ea98aab50abf208a422bc008eaec13f61f7` |

Package: [@anthropic-ai/claude-code 2.1.251](https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.251)

The extracted binary reports `2.1.251 (Claude Code)` and has ELF build ID
`77182fdf9abdf4942c072f3f73059aacd7a33d73`. The npm registry integrity
values were independently recomputed and matched:

- wrapper: `sha512-eG+ZPPpW2Dbmnntf1Fz9/T9ewS8I8SKfc1tcU2PqSwmftfjRPP7BXPaCyLuZ8kvgTdiPnJi/2/JnTvTRieneEQ==`;
- Linux x64: `sha512-HJyCY1ynzlsBk+N02IJeBNNZmzyd43lMuff49IXtbUDGHlf2XFHcxwYJEWCwIW51J3Hl4MvrqM6Ye8PGpJRIiA==`.

## Reproduction

Fetch, extract, and fingerprint the same immutable package versions:

```bash
probe_dir=$(mktemp -d)
npm pack --pack-destination "$probe_dir" @anthropic-ai/claude-code@2.1.251
npm pack --pack-destination "$probe_dir" @anthropic-ai/claude-code-linux-x64@2.1.251
mkdir -p "$probe_dir/native"
tar -xzf "$probe_dir/anthropic-ai-claude-code-linux-x64-2.1.251.tgz" \
  -C "$probe_dir/native"
sha256sum "$probe_dir"/*.tgz "$probe_dir/native/package/claude"
"$probe_dir/native/package/claude" --version
npm view @anthropic-ai/claude-code@2.1.251 dist --json
npm view @anthropic-ai/claude-code-linux-x64@2.1.251 dist --json
```

The Linux native package embeds the bundled JavaScript payload. Static
inspection identified three consecutive responsibilities in that payload: a
string tokenizer, a scalar-or-array normalizer, and the filesystem-agent
wrapper that converts missing/null to an empty array. These decimal byte
offsets make the inspection repeatable for the exact binary hash above:

| Offset | Evidence |
|---:|---|
| 175563008 | comma/literal-space tokenizer with parenthesis guard |
| 180523403 | scalar-or-string-array frontmatter schema |
| 180528618 | agent `skills` field declaration |
| 180531359 | scalar-or-array normalization and string-member filtering |
| 180531706 | filesystem-agent missing/null wrapper |
| 181355627 | normalized `skills` assignment |
| 181356267 | normalized array passed downstream |

Use `rg -a --byte-offset -o` against `$probe_dir/native/package/claude` to
locate the corresponding minified declarations. The separate `--agents` JSON
path rejects non-array `skills`, confirming that it is a different contract.

The recovered filesystem behavior is:

- missing, null, unsupported scalars, and mappings normalize to `[]`;
- a string becomes the tokenizer's single input;
- an array retains only direct string members before tokenization;
- comma and literal ASCII space split tokens outside parentheses;
- ECMAScript `trim()` removes edge whitespace and empty tokens;
- order and duplicates are retained;
- an exact `*` token collapses the result to `["*"]`.

Executable characterization lives in
`packages/skilllint/tests/test_ag_series.py`. It covers scalar/list parity,
mixed arrays, separators, parenthesis behavior, ECMAScript trim edge cases,
wildcard collapse, raw model round-tripping, and idempotent unrelated fixes.

## Scope and refresh rule

This evidence applies only to Markdown filesystem agents in Claude Code
2.1.251. It does not define the stricter `--agents` JSON or Agent SDK contract.
Only the Linux x64 glibc package was inspected; cross-platform parity is not
established. Minified symbol names and byte offsets are release-specific.
`claude plugin validate` accepts the characterized shapes but does not expose
their normalized output, so the exact output contract comes from the inspected
loader code rather than that validator.
Re-audit the published package, update the fingerprints, and rerun the
characterization tests before claiming parity with another Claude Code
version.
