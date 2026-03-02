# Architecture

**Analysis Date:** 2026-03-02

## Pattern Overview

**Overall:** Layered validation framework with protocol-based extensibility

**Key Characteristics:**
- Plugin/skill validation pipeline using composable validators
- PEP 723 standalone scripts for CLI entry points (plugin_validator.py, auto_sync_manifests.py)
- Shared library layer for frontmatter models and utilities (no scripts, importable by others)
- Token-based complexity measurement for skill content analysis
- Pydantic-based frontmatter schema validation
- Protocol-based validator interface for loose coupling

## Layers

**Entry Point & CLI:**
- Purpose: Expose validation and synchronization functionality via command line
- Location: `packages/skilllint/plugin_validator.py`, `packages/skilllint/auto_sync_manifests.py`
- Contains: PEP 723 standalone scripts with Typer CLI handlers
- Depends on: Validation layer, utility layer, Pydantic models
- Used by: Direct invocation via `uv run` (CLI), pre-commit hooks

**Validation Framework:**
- Purpose: Core validation logic for skills, agents, commands, plugins
- Location: `packages/skilllint/plugin_validator.py` (classes FrontmatterValidator, SkillComplexityValidator, etc.)
- Contains: Validator classes, error codes, validation result aggregation
- Depends on: Frontmatter models, utility functions, Pydantic
- Used by: CLI layer for batch validation, fix operations

**Data Models & Schema:**
- Purpose: Define validation schemas for frontmatter types (skills, agents, commands)
- Location: `packages/skilllint/frontmatter_core.py`
- Contains: Pydantic models (SkillFrontmatter, CommandFrontmatter, AgentFrontmatter), constants, registry
- Depends on: Pydantic only
- Used by: Validation framework, utility layer

**YAML I/O & Utilities:**
- Purpose: Handle YAML/frontmatter parsing with round-trip formatting preservation
- Location: `packages/skilllint/frontmatter_utils.py`
- Contains: RuamelYAMLHandler, load/dump functions, field update helpers
- Depends on: python-frontmatter, ruamel.yaml
- Used by: Validators performing fixes, frontmatter reading/writing

**Testing Infrastructure:**
- Purpose: Shared pytest fixtures for validator testing
- Location: `packages/skilllint/tests/conftest.py`
- Contains: CliRunner setup, sample directory builders, invalid/broken sample data
- Depends on: pytest, Typer testing utilities
- Used by: All test modules

## Data Flow

**Validation Workflow:**

1. User invokes `plugin_validator.py` with target path and options
2. CLI handler parses arguments (path, format, filter, ignore-config)
3. Path discovery phase finds validatable files matching patterns (skills/*/SKILL.md, agents/*.md, commands/*.md, plugin.json, hooks.json)
4. For each discovered file:
   - Detect FileType (skill, agent, command, plugin, hook, etc.)
   - Instantiate appropriate validator(s) based on file type
   - Validator reads file, extracts/parses content
   - Runs validation checks, returns ValidationResult
   - Filter results against ignore config if present
   - Aggregate issues by file
5. Report generation: Format results, count issues by severity, emit to console or JSON
6. Exit with status code based on error presence

**State Management:**
- Input state: File system (skills directories, markdown files, plugin.json manifests)
- Processing state: ValidationResult objects (passed, errors, warnings, info)
- Output state: Console report or JSON file with aggregated results

**Fix Workflow:**

1. User invokes with `--fix` flag
2. Validators supporting fixes (can_fix() returns True) are invoked
3. Fixes are collected as descriptive strings
4. Modified files are written back with preserved YAML formatting
5. Summary report shows applied fixes per file

## Key Abstractions

**Validator Protocol:**
- Purpose: Define common interface for all validators
- Location: `packages/skilllint/plugin_validator.py` (lines 696-732)
- Pattern: Protocol-based duck typing
- Methods: `validate(path) -> ValidationResult`, `can_fix() -> bool`, `fix(path) -> list[str]`
- Implementation classes: FrontmatterValidator, SkillComplexityValidator, InternalLinkValidator, etc.

**FileType Enum:**
- Purpose: Classify files by structure for routing to appropriate validators
- Location: `packages/skilllint/plugin_validator.py` (lines 566-610)
- Pattern: StrEnum with static method for detection from Path
- Values: SKILL, AGENT, COMMAND, PLUGIN, HOOK_CONFIG, HOOK_SCRIPT, CLAUDE_MD, REFERENCE, MARKDOWN, UNKNOWN

**ValidationResult & ValidationIssue:**
- Purpose: Encapsulate validation outcomes and individual problems
- Location: `packages/skilllint/plugin_validator.py` (lines 614-646)
- Pattern: Frozen dataclasses for immutability
- Fields: file path, severity (error/warning/info), code, message, line number, suggestion, docs URL

**Frontmatter Models:**
- Purpose: Schema validation for YAML frontmatter using Pydantic
- Examples: `SkillFrontmatter`, `CommandFrontmatter`, `AgentFrontmatter` in `frontmatter_core.py`
- Pattern: Pydantic BaseModel with field validators for normalization (array->CSV, multiline->singleline)
- Extensions: Open/Closed principle — new models added to registry without changing existing code

**ComplexityMetrics:**
- Purpose: Token-based skill content analysis
- Location: `packages/skilllint/plugin_validator.py` (lines 655-688)
- Pattern: Dataclass with computed properties (status, message)
- Thresholds: TOKEN_WARNING_THRESHOLD=4400, TOKEN_ERROR_THRESHOLD=8800 (body tokens)

## Entry Points

**plugin_validator.py:**
- Location: `packages/skilllint/plugin_validator.py`
- Triggers: CLI invocation or pre-commit hook
- Responsibilities:
  - Parse arguments (--path, --format, --fix, --ignore-config, --filter-type)
  - Discover validatable files
  - Run validators
  - Generate reports (console/JSON)
  - Apply fixes if requested
  - Exit with appropriate status code

**auto_sync_manifests.py:**
- Location: `packages/skilllint/auto_sync_manifests.py`
- Triggers: Pre-commit hook or manual invocation with `--reconcile`
- Responsibilities:
  - Detect plugin CRUD operations from git staging
  - Parse plugin.json and marketplace.json
  - Update manifests with discovered components
  - Bump versions (major/minor/patch) based on change type
  - Write updated manifests back

## Error Handling

**Strategy:** Specific error codes with three-tier severity (error/warning/info), fixable vs. non-fixable issues

**Patterns:**
- Frontmatter errors (FM001-FM010): YAML syntax, required fields, type mismatches
- Skill errors (SK001-SK009): Name format, description length, token thresholds, directory naming
- Link errors (LK001-LK002): Broken references, missing ./ prefixes
- Progressive disclosure (PD001-PD003): Missing standard directories (references/, examples/, scripts/)
- Plugin errors (PL001-PL005): Missing manifest, invalid JSON, path validation
- Hook errors (HK001-HK005): Invalid hooks.json, missing executables
- Namespace reference errors (NR001-NR002): Target does not exist or escapes scope
- Plugin registration errors (PR001-PR005): Capability exists but not registered, metadata gaps

All error codes map to documentation URLs generated by `generate_docs_url()`.

## Cross-Cutting Concerns

**Logging:** Rich console output with formatted panels, spinners, and tables for complex results. Structured JSON output available via `--format json`

**Validation:** Multi-pass approach — frontmatter schema validation first (Pydantic), then cross-file validation (links, registered components), then token-based complexity

**File Type Detection:** Path-based heuristics (filename, directory membership, file extension) applied early to route to appropriate validators

**YAML Formatting:** Round-trip YAML handler preserves formatting during fixes; unnecessary quotes stripped, special characters quoted only when required by YAML syntax

**Token Counting:** OpenAI cl100k_base encoding used for all complexity measurement; frontmatter and body counted separately for granular metrics

---

*Architecture analysis: 2026-03-02*
