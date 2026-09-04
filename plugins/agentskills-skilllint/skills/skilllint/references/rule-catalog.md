# skilllint Rule Catalog

Complete reference for all rule IDs emitted by `skilllint`. Use `skilllint check --verbose <path>` to see explanatory text alongside each violation.

---

## FM — Frontmatter Rules

Validate YAML frontmatter in SKILL.md, agent .md, and command .md files.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| FM001 | warning | no | Frontmatter block is missing entirely |
| FM002 | error | no | Frontmatter is not valid YAML |
| FM003 | error | no | Required frontmatter field is missing (e.g. `name` per agentskills spec) |
| FM004 | warning | **yes** | `description` uses a YAML multiline block scalar (`` >- ``, `` \| ``, `` \|- ``); Claude Code skill indexer reads this as literal `>-`. Use a single-line string. |
| FM005 | error | no | A frontmatter field has the wrong data type (e.g. a boolean field given a string value) |
| FM006 | error | no | A frontmatter field holds a value outside its closed enum (e.g. an invalid `effort` or `permissionMode`) |
| FM007 | warning | **yes** | `tools`, `allowed-tools`, or `disallowedTools` is a YAML array instead of a comma-separated string |
| FM009 | info | **yes** | Unquoted colon in `description` or other string field causes YAML parse failure |
| FM010 | error | **yes** | Skill `name` syntax, length, pattern, and directory equality |

---

## SK — Skill Quality Rules

Validate skill name, description quality, and token budget.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| SK004 | warning | no | Skill description is very short (< 20 chars); may not trigger auto-invocation |
| SK005 | warning | no | Skill description lacks trigger phrases ("Use when...", keywords); Claude may not auto-invoke |
| SK006 | warning | no | Skill body is large (over `TOKEN_WARNING_THRESHOLD` tokens); consider splitting |
| SK007 | error | no | Skill body exceeds token limit (`TOKEN_ERROR_THRESHOLD`); must be split into sub-skills |
| SK008 | error | no | Skill directory name violates the naming convention (lowercase, digits, hyphens; must match `name`) |
| SK009 | info | no | `plugin.json` lists `skills` explicitly, so Claude Code uses manual selection instead of auto-discovery |

**Token limit fix (SK006/SK007):** Move large sections to `skills/<name>/references/<file>.md` and add a link from SKILL.md. Thresholds are `TOKEN_WARNING_THRESHOLD` (warning) and `TOKEN_ERROR_THRESHOLD` (error) — body text only, frontmatter excluded. Run `skilllint rules` to see current values.

---

## AS — AgentSkills Open Standard Rules

Cross-platform compliance with the [agentskills.io](https://agentskills.io) specification.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| AS001 | error | no | `SKILL.md` declares no `name` field (required by the AgentSkills spec; `skills.md` treats it as optional, so no FM rule covers this) |
| AS006 | info | no | No evaluation queries file found (optional but recommended) |
| AS008 | warning | no | MCP tool name casing does not match the referenced server (case is significant) |
| AS009 | warning | no | Nested skill will not be auto-discovered — skills must be direct children of `skills/` |

**Retired:** AS002–AS005 are folded into the FM series (`name` syntax and
directory equality into FM010, `description` presence into FM001, unquoted
colons into FM009, body token budget into SK006/SK007). AS007 was deleted
outright, with no replacement — see `docs/registry-schema-examples.md`.

**Full detail:** Use `skilllint check --filter <ID> --verbose <path>` (e.g. `skilllint check --filter AS006 --verbose <path>`) to see detailed output for any AS rule.

---

## LK — Internal Link Rules

Validate internal markdown links in SKILL.md and agent files.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| LK001 | error | no | Internal link target file does not exist on disk |

**LK001 fix:** Verify the linked file path is correct. Links in `skills/<name>/SKILL.md` are relative to the skill directory, not the plugin root.

---

## PD — Progressive Disclosure Rules

Validate the `references/` directory structure for progressive disclosure.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PD001 | info | no | Skill directory has no `references/` subdirectory for supporting documentation |
| PD002 | info | no | Skill directory has no `examples/` subdirectory for usage samples |
| PD003 | info | no | Skill directory has no `scripts/` subdirectory for helper scripts |

---

## PL — Plugin Manifest Rules

Validate `plugin.json` structure.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PL001 | error | no | `plugin.json` is missing |
| PL002 | error | no | `plugin.json` is not valid JSON |
| PL003 | error | no | Required `name` field is missing from `plugin.json` |
| PL004 | error | no | A path in `plugin.json` does not start with `./` |
| PL005 | error | no | Referenced file in `plugin.json` does not exist |
| PL006 | error | no | `marketplace.json` has an unrecognized top-level key; see [Claude Code marketplace schema](https://code.claude.com/docs/en/plugin-marketplaces.md#marketplace-schema) for the documented root keys (skilllint#114) |

---

## PA — Plugin-packaged agent frontmatter

Anthropic documents that **plugin** subagents do not support `hooks`, `mcpServers`, or `permissionMode` in agent frontmatter (ignored when loading from a plugin). Authority: [Choose the subagent scope](https://docs.anthropic.com/en/docs/claude-code/sub-agents.md#choose-the-subagent-scope).

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PA001 | error / warning | no | `permissionMode` → error; `hooks` / `mcpServers` → warnings with plugin-level cross-checks (`.mcp.json`, `hooks/hooks.json`) |

---

## AG — Agent Frontmatter Rules

Validate Claude Code `agents/*.md` frontmatter on every Claude agent file regardless of scope (personal, project, or plugin) — unlike PA (above), which is plugin-scoped only. Authority: [Create custom subagents](https://code.claude.com/docs/en/sub-agents#available-tools).

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| AG001 | error | no | Every entry in `tools` is an unscoped wildcard (e.g. `mcp__*`, bare `*`) that names no server — the subagent fails to launch |
| AG002 | error / warning | no | MCP tool name in `tools` or `disallowedTools` has a case mismatch with a discovered server (error) or references a server not found in any discovered config (warning) |
| AG003 | warning | no | Claude Code discards at least part of `skills`: a non-string scalar or mapping is discarded, while a sequence passes string members through runtime normalization and discards non-string members |

**AG003 file-loader contract:** Omitted, null, empty-string, and empty-list values are clean. A scalar string and a sequence containing only strings are also clean and normalize to a string list. Other scalar or mapping values are discarded and warn once; a sequence containing any non-string member passes its strings through runtime normalization, discards the rest, and warns once. This rule follows the Markdown agent loader verified in [Claude Code 2.1.251](https://www.npmjs.com/package/@anthropic-ai/claude-code/v/2.1.251), not the separate strict `--agents` / Agent SDK input, and it neither requires YAML-list syntax nor auto-fixes the authored shape.

**Scope vs. AS008:** AG001 and AG002 validate an agent's `tools` field. AS008 is a separate rule that validates only `allowed-tools` on `SKILL.md` under agentskills.io authority; AG002 validates `tools`/`disallowedTools` on agent files under sub-agents.md authority.

---

## HK — Hook Rules

Validate `hooks.json` and inline hook configurations.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| HK001 | error | no | `hooks.json` is not valid JSON |
| HK002 | error | no | Hook event name is not a recognized Claude Code event |
| HK003 | error | no | Hook `type` is not one of: `command`, `prompt`, `agent` |
| HK004 | error | no | Hook script path does not exist on disk |
| HK005 | warning | no | Hook script is not executable (`chmod +x` required) |

---

## NR — Namespace Reference Rules

Validate namespace-qualified skill references (e.g. `plugin-name:skill-name`).

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| NR001 | error | no | Namespace reference uses a plugin name that is not installed |
| NR002 | error | no | Namespace reference attempts path traversal or uses disallowed path segments (e.g., `..`, `/`, `\`) within the plugin prefix or target name |

---

## SL — Symlink Rules

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| SL001 | error | **yes** | Symlink target has trailing whitespace or newline characters |

---

## TC — Token Count

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| TC001 | info | no | Token count report for a file (always shown with `--verbose`; use `--tokens-only` for integer output) |

---

## PR — Plugin Registration Rules

Validate `plugin.json` capability registration (skills, agents, commands arrays).

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PR001 | warning | no | Capability exists but not explicitly registered in `plugin.json` |
| PR002 | error | no | Registered capability path does not exist on the filesystem |
| PR003 | info | no | Plugin metadata fields not populated (`repository`, `homepage`, `author`) |
| PR004 | warning | no | Plugin metadata repository URL mismatches git remote URL |
| PR005 | error | no | Registered command path is a skill directory (contains `SKILL.md`) |

---

## CU — Cursor `.mdc` Frontmatter Rules

These only fire when `--platform cursor` is used.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| CU001 | error | no | Required field missing from `.mdc` frontmatter |
| CU002 | error | no | Unknown field in `.mdc` frontmatter |

---

## CX — Codex Platform File Rules

These only fire when `--platform codex` is used.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| CX001 | error | no | `AGENTS.md` content is empty |
| CX002 | error | no | Unknown field in `prefix_rule()` block |

---

## Quick Reference: Auto-Fixable Rules

Run `skilllint check --fix <path>` to automatically fix:

- **FM004** — multiline block scalar in description
- **FM007** — tools / allowed-tools / disallowedTools as YAML array
- **FM009** — unquoted colon in string field
- **FM010** — skill name syntax and name/directory mismatch
- **SL001** — symlink outside plugin directory

All other rules (including SK006/SK007 token size, PD, LK, HK series) require manual fixes.
