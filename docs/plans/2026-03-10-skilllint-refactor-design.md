# skilllint Package Refactor — Design

## Goal

Decompose `packages/skilllint/plugin_validator.py` (5,695 lines) into a proper package layout modelled on ruff's crate structure, eliminating agent context-window friction during development.

## Architecture

Models sit at the bottom of the dependency graph (no deps). Validators depend only on models. Reporters depend only on models. CLI depends on everything. Integration utilities are injected into validators as context — validators never call git/AI directly.

## Package Layout

```
packages/skilllint/skilllint/
├── models.py              # ValidationIssue, ValidationResult, ErrorCode, FileType — no deps
├── validators/
│   ├── __init__.py        # ALL_VALIDATORS registry, built from @skilllint_rule decorators
│   ├── frontmatter.py     # FrontmatterValidator, NameFormatValidator, DescriptionValidator
│   ├── structure.py       # PluginStructureValidator, PluginRegistrationValidator
│   ├── complexity.py      # ComplexityValidator, MarkdownTokenCounter
│   ├── links.py           # InternalLinkValidator, NamespaceReferenceValidator, SymlinkTargetValidator
│   ├── hooks.py           # HookValidator
│   └── disclosure.py      # ProgressiveDisclosureValidator
├── reporters/
│   ├── __init__.py
│   ├── console.py         # ConsoleReporter (Rich-based)
│   ├── ci.py              # CIReporter (plain text)
│   └── summary.py         # SummaryReporter (one-line status)
├── integration/
│   ├── __init__.py
│   ├── git.py             # git utilities (_git_bash_path, _get_git_remote_url, etc.)
│   ├── claude.py          # Claude AI integration (validate_with_claude)
│   └── ignore.py          # ignore pattern support
├── adapters/              # existing — Phase 2 (unchanged)
├── rules/                 # existing — Phase 2 (unchanged)
├── cli.py                 # thin Typer app — entry point only, no domain logic
├── rule_registry.py       # @skilllint_rule decorator + registry dict + `skilllint rule` lookup
└── plugin_validator.py    # temporary re-export shim → deleted after migration complete
```

## Rule Registry Design

Each validator function is decorated with `@skilllint_rule`:

```python
@skilllint_rule(
    "SK001",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],  # "agentskills" = base class, inherited by all platforms
)
def check_name_field(frontmatter: dict, path: Path) -> list[ValidationIssue]:
    """
    ## SK001 — Missing `name` field

    Every SKILL.md must declare a `name` field in its frontmatter.

    **Fix:** Add `name: your-skill-name` to the frontmatter block.

    **References:**
    - https://docs.agentskills.io/spec/frontmatter#name
    """
```

The decorator registers `{id → RuleEntry(fn, id, severity, category, platforms, docstring)}` in a global `RULE_REGISTRY` dict.

`skilllint rule SK001` renders the docstring via Rich. Runtime output stays terse (`SK001  error  missing name field  SKILL.md:3`).

`platforms=["agentskills"]` means the rule applies to all platforms. Platform-specific rules declare their platforms explicitly (e.g. `platforms=["claude-code"]`).

## Dependency Rules (invariants)

1. `models.py` imports nothing from `skilllint`
2. `validators/*` imports from `models` only — never from `reporters`, `cli`, or `integration`
3. `reporters/*` imports from `models` only — never from `validators` or `cli`
4. `integration/*` imports from `models` only
5. `cli.py` is the only module allowed to import from all layers
6. `rule_registry.py` imports from `models` only

## Migration Strategy

Incremental — keep `plugin_validator.py` as a re-export shim during migration so existing tests pass throughout:

1. Extract `models.py` first (zero risk — pure data)
2. Extract `rule_registry.py` (no deps on validators yet)
3. Extract `integration/` modules (git, claude, ignore)
4. Extract `reporters/` modules one at a time
5. Extract `validators/` modules one at a time, adding `@skilllint_rule` decorators
6. Write `cli.py` as thin wirer
7. Update `pyproject.toml` entry points to `skilllint.cli:app`
8. Delete `plugin_validator.py` shim

Tests must stay green after every step.

## `skilllint rule` Command

New Typer sub-command in `cli.py`:

```python
@app.command("rule")
def show_rule(rule_id: str):
    """Show documentation for a rule ID."""
    entry = RULE_REGISTRY.get(rule_id.upper())
    if not entry:
        console.print(f"[red]Unknown rule: {rule_id}[/red]")
        raise typer.Exit(1)
    console.print(Markdown(entry.docstring))
```

`skilllint rules --platform claude-code` lists all rules for a platform.
`skilllint rules --category frontmatter` lists all rules in a category.
