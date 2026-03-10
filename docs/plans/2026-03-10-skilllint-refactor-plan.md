# skilllint Package Refactor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decompose plugin_validator.py (5,695 lines) into a proper package layout — models, validators, reporters, integration, cli — with a @skilllint_rule decorator registry and `skilllint rule <ID>` command.

**Architecture:** Models at bottom of dep graph. Validators/reporters depend on models only. CLI wires everything. Rule decorator registers each validator function with id, severity, category, platforms, and docstring for `skilllint rule` lookup.

**Tech Stack:** Python 3.11+, Typer, Rich, uv, pytest

---

## Task 1: Create `models.py`

Extract `ValidationIssue`, `ValidationResult`, `ErrorCode`, `FileType`, `YamlValue`, `ComplexityMetrics` dataclasses/enums from `plugin_validator.py` into `packages/skilllint/models.py`. Update imports in `plugin_validator.py` to import from `models`. Tests must stay green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 2: Create `rule_registry.py`

Implement `@skilllint_rule(id, severity, category, platforms)` decorator and `RULE_REGISTRY` dict. No validator functions yet — just the decorator infrastructure and `RuleEntry` dataclass. Write tests for the decorator registration.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 3: Add `skilllint rule` and `skilllint rules` CLI commands

Add `rule` and `rules` sub-commands to the Typer app in `plugin_validator.py` (before `cli.py` exists). `rule <ID>` renders docstring via Rich Markdown. `rules` lists all registered rules with optional `--platform` and `--category` filters. Write tests. (Registry will be empty until validators are migrated — commands work but return empty.)

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 4: Create `integration/ignore.py`

Extract `_load_ignore_patterns`, `_is_ignored`, `_load_ignore_config`, `IgnoreConfig`, `_is_suppressed`, `_filter_result_by_ignore` into `packages/skilllint/integration/ignore.py`. Update imports in `plugin_validator.py`. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 5: Create `integration/git.py`

Extract `_git_bash_path`, `_should_skip_claude_validate`, `_get_git_remote_url`, `_get_git_author`, `_git_file_has_execute_bit`, `get_staged_files` into `packages/skilllint/integration/git.py`. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 6: Create `integration/claude.py`

Extract `is_claude_available`, `validate_with_claude` into `packages/skilllint/integration/claude.py`. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 7: Create `reporters/console.py`, `reporters/ci.py`, `reporters/summary.py`

Extract `Reporter` protocol, `ConsoleReporter`, `CIReporter`, `SummaryReporter` into their respective modules. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 8: Create `validators/disclosure.py`

Extract `ProgressiveDisclosureValidator` into `packages/skilllint/validators/disclosure.py`. Add `@skilllint_rule` decorators to its check methods. Update imports. Run full suite.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 9: Create `validators/links.py`

Extract `InternalLinkValidator`, `NamespaceReferenceValidator`, `SymlinkTargetValidator`. Add `@skilllint_rule` decorators. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 10: Create `validators/complexity.py`

Extract `ComplexityValidator`, `MarkdownTokenCounter`. Add `@skilllint_rule` decorators. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 11: Create `validators/hooks.py`

Extract `HookValidator`. Add `@skilllint_rule` decorators. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 12: Create `validators/structure.py`

Extract `PluginStructureValidator`, `PluginRegistrationValidator`. Add `@skilllint_rule` decorators. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 13: Create `validators/frontmatter.py`

Extract `FrontmatterValidator`, `NameFormatValidator`, `DescriptionValidator`. Add `@skilllint_rule` decorators. Update imports. Tests green.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 14: Create `validators/__init__.py` with ALL_VALIDATORS registry

Build `ALL_VALIDATORS` list from `RULE_REGISTRY`. Verify `skilllint rules` now lists all migrated rules.

Write failing test → confirm RED → implement → confirm GREEN → commit.

## Task 15: Create `cli.py` and update entry points

Write `packages/skilllint/cli.py` as thin Typer app importing from all layers. Update `pyproject.toml` entry points to `skilllint.cli:app`. Delete re-export shim from `plugin_validator.py`. Full suite green. Verify `skilllint rule SK001` works end-to-end.

Write failing test → confirm RED → implement → confirm GREEN → commit.

---

Each task: write failing test → run to confirm RED → implement → run to confirm GREEN → commit.
