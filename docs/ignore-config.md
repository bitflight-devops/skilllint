# Ignore configuration reference

skilllint supports per-directory and per-plugin suppression of rule violations via config files. Rules are suppressed from *reporting* only — `--fix` still runs for suppressed rules.

---

## `.skilllint.json` — directory-level config

Place `.skilllint.json` at any directory level. When validating a file, skilllint walks up from that file's directory and uses the nearest `.skilllint.json` it finds.

```json
{
  "ignore": {
    "": ["AS008"],
    "skills/legacy": ["LK002", "SK006"],
    "agents/generated": ["FM004", "FM007", "FM009"]
  }
}
```

**Key semantics:**

| Key | Matches |
|---|---|
| `""` (empty string) | All files under the directory containing this config file |
| `"skills/legacy"` | Files whose path relative to the config file starts with `skills/legacy` |
| `"agents/generated/my-agent.md"` | That exact file only |

Prefix matching is used: `"skills"` suppresses `skills/foo/SKILL.md`, `skills/bar/SKILL.md`, etc.

**Discovery and caching:**

- Discovery walks up from each file's parent directory to the filesystem root, stopping at the first `.skilllint.json` or plugin root found.
- Results are cached per directory within a single `check` run, so directories shared by many files are only walked once.

**Example — suppress AS008 globally for an entire repo:**

```json
{
  "ignore": {
    "": ["AS008"]
  }
}
```

Place this at the repo root. Every file skilllint scans under that root will have AS008 suppressed.

**Example — suppress LK002 for one subdirectory:**

```
my-repo/
  .skilllint.json          ← suppress LK002 under .agents/skills/legacy/
  .agents/
    skills/
      legacy/
        SKILL.md
```

```json
{
  "ignore": {
    ".agents/skills/legacy": ["LK002"]
  }
}
```

---

## `.claude-plugin/validator.json` — plugin-level config

For files inside a plugin (a directory containing `.claude-plugin/plugin.json`), place suppression config at `.claude-plugin/validator.json`. Plugin-level config takes priority over any `.skilllint.json` in a parent directory.

```json
{
  "ignore": {
    "": ["PA001"],
    "agents/generated": ["FM004", "FM007"],
    "skills/vendor": ["SK006", "AS005"]
  }
}
```

The key format is identical to `.skilllint.json`. Keys are relative to the plugin root (the directory containing `.claude-plugin/`).

---

## Priority and precedence

1. **Plugin root** (`.claude-plugin/validator.json`) — highest priority when inside a plugin
2. **Nearest `.skilllint.json`** — used when no plugin root is found, or outside plugin boundaries

Only one config file is used per file — the nearest one found while walking up. Config files do not stack or merge.

---

## Rule codes

Run `skilllint rules` to list all available rule codes and their descriptions.

```bash
skilllint rule LK002   # show detail for one rule
skilllint rules        # list all rules
```
