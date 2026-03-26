# Handoff: Rule Documentation System

**Date:** 2026-03-24
**Status:** Phase 1 complete, Phase 2 ready to start
**Branch:** main (uncommitted changes)

## What was done

### Problem
`skilllint rule <code>` only works for 9 of 44+ rules (AS001-AS008, PA001). The rest are ErrorCode enum members not registered in RULE_REGISTRY. No rule has fixture-backed examples or spec citations.

### Phase 1 (COMPLETE — uncommitted on working tree)

1. **ValidationIssue + ValidationResult** migrated from frozen dataclasses to Pydantic BaseModel
   - `code` field: `Annotated[str, Field(pattern=r"^[A-Z]{2}\d{3}$")]` — validates rule ID format at construction
   - Files: `packages/skilllint/plugin_validator.py`

2. **RuleEntry + RuleAuthority** migrated to Pydantic BaseModel
   - `severity` narrowed to `Literal["error", "warning", "info"]`
   - File: `packages/skilllint/rule_registry.py`

3. **Fixture infrastructure** created
   - `packages/skilllint/tests/fixture_loader.py` — `discover_fixtures()` + `FixtureCase`
   - `packages/skilllint/tests/test_rule_fixtures.py` — parametrized test runner (6 tests passing)
   - Directory: `packages/skilllint/tests/fixtures/providers/{agentskills,claude,cursor,gemini-cli,codex,copilot-cli}/{failing-examples,passing-examples}/`
   - `_future/` placeholders for .mcp.json, .lsp.json, settings.json, outputStyles

4. **3 seed fixtures** (one per complexity tier)
   - FM002 (Tier 1): invalid YAML syntax
   - AS008 (Tier 4): MCP server case mismatch in plugin context
   - HK005 (Tier 5): non-executable hook script (filesystem-dependent)

5. **Linter exclusions** for failing-examples in: pre-commit, ruff, ty, markdownlint, .gitattributes, skilllint --fix guard

6. **Adapter codes formalized**: CU001/CU002 (cursor), CX001/CX002 (codex) — replaced free-form strings

7. **pa_series.py** stale ErrorCode annotations fixed

8. **Failing-examples guard** fixed: `Path.parts` instead of string search

### Known issues (from Phase 1 review at `.claude/reports/phase1-review.md`)

- **H1**: 3 pre-existing test failures — 2 need `name: test-skill` in fixture strings, 1 is a real duplicate-validation bug (AS001 fires twice via both Claude-code and AgentSkills adapters on same file)
- **M1**: `importlib.util` loader in test_rule_fixtures.py is functional but fragile
- Test suite: 1027 passed, 1 skipped

## What needs to happen next

### Phase 2: FM-series migration (experiment)

Create `packages/skilllint/rules/fm_series.py` with 10 `@skilllint_rule` decorated functions.

**Pattern to follow** — AS001 in `packages/skilllint/rules/as_series.py`:
```python
@skilllint_rule(
    "FM001",
    severity="error",  # or "warning" — see severity classification
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": "https://code.claude.com/docs/en/skills.md#frontmatter-reference"},
)
def check_fm001(frontmatter, path, file_type):
    """## FM001 — Missing required frontmatter field

    Skills require `description` (recommended). Agents require both `name` and `description`.

    **Source:** skills.md frontmatter reference — `name` is optional for skills, required for agents.
    sub-agents.md — `name` and `description` are Required: Yes.

    **Fix:** Add the missing field to the YAML frontmatter block.

    <!-- examples: FM001 -->
    """
```

**Severity classifications** (from `.claude/reports/severity-fm-series.md`):

| Rule | Current | Should Be | Notes |
|------|---------|-----------|-------|
| FM001 | error | error (agents) / warning (skills) | Needs file-type-aware severity |
| FM002 | error | error (SCHEMA) | |
| FM003 | error | error (SCHEMA) | |
| FM004 | warning | warning (RECOMMENDATION) | |
| FM005 | error | error (SCHEMA) | |
| FM006 | error | error (SCHEMA) | |
| FM007 | warning | warning (RECOMMENDATION) | |
| FM008 | warning | warning (RECOMMENDATION) | |
| FM009 | info | info (INFORMATIONAL) | |
| FM010 | error | error (SCHEMA) | |

**Steps:**
1. Create `rules/fm_series.py` — 10 decorated functions with docstrings citing specs
2. Refactor `FrontmatterValidator` to thin adapter calling fm_series functions
3. Fix FM001 file-type-aware severity
4. Create FM001-FM010 fixture directories (failing + passing) under `fixtures/providers/agentskills/`
5. Add `<!-- examples: FM001 -->` markers to each docstring
6. Update `_show_rule_doc()` to resolve markers via `discover_fixtures()`
7. Import fm_series in `rules/__init__.py`
8. Verify `skilllint rule FM001` through `FM010` all work

### Phase 3: Remaining series (same pattern, one at a time)

SK → HK → PL → PR → LK → PD → NR → SL → TC → CM

Severity classifications in:
- `.claude/reports/severity-sk-series.md`
- `.claude/reports/severity-hk-pl-pr-pa-series.md`
- `.claude/reports/severity-as-lk-pd-nr-sl-tc-cm-series.md`

**Severity changes needed:**
- AS003: error → warning (description is "Recommended" not "Required")
- AS005: error threshold → warning (no spec authority)
- SK007: error → warning (no spec-defined hard limit)
- PL001: error → info (spec says manifest is optional)
- SL001: warning → error (broken symlinks are functional failures)
- Remove CM001 and NR002 (dead — never emitted)

### Phase 4: Delete ErrorCode enum

After all series migrated. See `.claude/reports/errorcode-migration-analysis.md` for the full plan.

### Phase 5: Telemetry

Design at `.claude/reports/fixture-maintenance-process.md` (Scenario 4).

## Key files and reports

| File | Purpose |
|------|---------|
| `.claude/reports/rule-citation-audit.md` | What each rule cites today |
| `.claude/reports/full-validation-surface.md` | What skilllint validates today (14 validators, 54 error codes) |
| `.claude/reports/plugin-spec-surface.md` | What the spec says should be validatable (with citations) |
| `.claude/reports/severity-fm-series.md` | FM001-FM010 severity classification |
| `.claude/reports/severity-sk-series.md` | SK001-SK009 severity classification |
| `.claude/reports/severity-hk-pl-pr-pa-series.md` | HK/PL/PR/PA severity classification |
| `.claude/reports/severity-as-lk-pd-nr-sl-tc-cm-series.md` | AS/LK/PD/NR/SL/TC/CM severity classification |
| `.claude/reports/errorcode-migration-analysis.md` | How ErrorCode is consumed, migration phases |
| `.claude/reports/fixture-infrastructure-design.md` | Fixture directory layout, loader, test runner design |
| `.claude/reports/fixture-maintenance-process.md` | 5 scenarios for keeping fixtures in sync |
| `.claude/reports/phase1-review.md` | Code review of Phase 1 changes |
| `.claude/reports/rule-fixture-requirements.md` | What directory structure each rule needs |

## Spec files on disk

Downloaded and available at:
- `/tmp/plugins-reference.md` — full plugin.json schema, all file types
- `/tmp/hooks.md` — 22 hook events, 4 hook types, full schema
- `/tmp/skills.md` — skill frontmatter schema
- `/tmp/sub-agents.md` — agent frontmatter schema
- `/tmp/agent-development-skill.md` — official plugin-dev agent development skill (color field, agent constraints)

**These are in /tmp and will not survive reboot.** Re-download with:
```bash
curl -sL "https://code.claude.com/docs/en/plugins-reference.md" -o /tmp/plugins-reference.md
curl -sL "https://code.claude.com/docs/en/hooks.md" -o /tmp/hooks.md
curl -sL "https://code.claude.com/docs/en/skills.md" -o /tmp/skills.md
curl -sL "https://code.claude.com/docs/en/sub-agents.md" -o /tmp/sub-agents.md
curl -sL "https://raw.githubusercontent.com/anthropics/claude-code/main/plugins/plugin-dev/skills/agent-development/SKILL.md" -o /tmp/agent-development-skill.md
```

## Vendor repos cloned

- `.claude/vendor/claude_code/` — anthropics/claude-code (official plugins, examples)
- `.claude/vendor/claude_cookbooks/` — anthropics/claude-cookbooks (skills, agents, hooks examples)

## Key design decisions

1. **Provider-first fixture layout** — `fixtures/providers/{platform}/{failing,passing}/{rule-id}/` not rule-id-first
2. **Pydantic for trust-boundary types** — ValidationIssue, ValidationResult, RuleEntry, RuleAuthority. Dataclasses for internal value objects.
3. **`code: Annotated[str, Field(pattern=...)]`** — validates rule ID format, caught real issues in cursor/codex adapters
4. **Schema error vs recommendation warning** — spec says MUST/required → error. Spec says recommended/should → warning. Citations required for every classification.
5. **Fixtures must trigger exactly ONE rule** — `allowed_collateral` in fixture.toml for structural cascades (e.g., FM002 broken YAML → AS001/AS003)
6. **`_future/` directory** for unvalidated file types — excluded from discovery, ready for when rules are implemented
7. **`<!-- examples: RULE_ID -->`** docstring markers resolved at display time by `_show_rule_doc`

## Uncommitted changes

Run `git diff --stat HEAD` to see all changes. These are NOT committed yet — review before committing.
