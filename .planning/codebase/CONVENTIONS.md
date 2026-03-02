# Coding Conventions

**Analysis Date:** 2026-03-02

## Naming Patterns

**Files:**
- PEP 723 scripts (entry points): Use snake_case with `.py` extension (e.g., `plugin_validator.py`, `auto_sync_manifests.py`)
- Test files: Follow pytest convention `test_*.py` (e.g., `test_frontmatter_validator.py`)
- Library modules (non-script imports): Use snake_case (e.g., `frontmatter_core.py`, `frontmatter_utils.py`)

**Functions:**
- Use snake_case for all functions: `_safe_load_yaml()`, `_dump_yaml()`, `validate()`, `fix()`, `get_frontmatter_model()`
- Private/internal functions: Prefix with single underscore (e.g., `_fix_unquoted_colons()`, `_normalize_skill_name()`)
- Helper functions at module level: Also use underscore prefix if not part of public API

**Variables:**
- Local variables and parameters: snake_case (e.g., `frontmatter_text`, `skill_md`, `plugin_dir`)
- Module-level constants: UPPER_SNAKE_CASE (e.g., `TOKEN_WARNING_THRESHOLD`, `TOKEN_ERROR_THRESHOLD`, `ERROR_CODE_BASE_URL`)
- Type aliases: PascalCase with `TypeAlias` annotation (e.g., `YamlValue`, `FrontmatterValue`)

**Types & Classes:**
- All classes: PascalCase (e.g., `SkillFrontmatter`, `CommandFrontmatter`, `AgentFrontmatter`, `FrontmatterValidator`)
- Enums (StrEnum): PascalCase (e.g., `ErrorCode`, `FileType`)
- Dataclasses: PascalCase (e.g., `ValidationIssue`, `ValidationResult`, `ComplexityMetrics`)
- Protocol classes: PascalCase (e.g., `Validator`, `Reporter`)
- Exception fields in camelCase WHEN matching external specifications (e.g., AgentFrontmatter uses `disallowedTools`, `permissionMode`, `mcpServers` per agent-schema.md spec) — document these exceptions with `# noqa: N815` ruff suppression

## Code Style

**Formatting:**
- Tool: Not explicitly configured; follows PEP 8 standards
- Line length: Appears to default to standard 88-character limit (Black-like)
- Imports: Organized by standard Python import order (stdlib → third-party → local)

**Linting:**
- Tool: Ruff (implied by codebase patterns and `.noqa` comments)
- Key rules enforced or suppressed:
  - `N815`: Suppress for camelCase in external schema fields (AgentFrontmatter)
  - `PLR0911`: Multiple return paths tolerated in utility functions
  - Ruff checks implied but not explicitly configured in worktree

## Import Organization

**Order (strict):**
1. Standard library (e.g., `from __future__ import annotations`, `import sys`, `from pathlib import Path`)
2. Third-party packages (e.g., `from pydantic import`, `from rich.console import`, `from ruamel.yaml import`)
3. Local/sibling modules (e.g., `from frontmatter_core import`, `from frontmatter_utils import`)
4. Conditional imports under `if TYPE_CHECKING:` (e.g., `from collections.abc import Generator`)

**Path Aliases:**
- PEP 723 scripts use `sys.path.insert(0, str(Path(__file__).parent))` to import co-located library modules
  - See `plugin_validator.py` lines 64-69: Exposes `frontmatter_core` and `frontmatter_utils` for import
  - See `conftest.py` lines 26-32: Uses `importlib.util` to load hyphenated module names (`plugin_validator`)

## Error Handling

**Patterns:**
- Use Pydantic's `ValidationError` for schema validation failures (caught and converted to `ValidationIssue` objects)
- Raise `NotImplementedError` when a validator's `fix()` method is not auto-fixable (e.g., ComplexityValidator)
- Catch `YAMLError` for YAML parsing failures with safe fallback behavior
- Catch git exceptions (`InvalidGitRepositoryError`, `NoSuchPathError`) with graceful None returns
- Return `tuple[bool, str]` patterns for integration layer functions (e.g., `validate_with_claude()` returns success bool + output message)
- Use early return guards for validation shortcuts (e.g., return None early if no frontmatter found)

**Raise vs Return:**
- Avoid broad exception handlers; let errors propagate unless there's specific recovery
- Use result tuples or Optional returns for graceful degradation (e.g., `_find_plugin_root()` returns `Path | None`)

## Logging

**Framework:** No explicit logging framework; uses print/Rich console for output
- Standard output: `Console()` from rich for formatted terminal output
- File output: Written to temp files or stdout capture by integration tests
- Patterns: Info/warning/error levels implied by Rich Panel styles ("info" green, "warning" yellow, "error" red)

## Comments

**When to Comment:**
- Docstrings on all public functions and classes (Google-style format with Args, Returns, Raises)
- Inline comments for non-obvious regex patterns (e.g., `_SKILL_DIR_NAME_PATTERN`)
- Section headers for major blocks (e.g., `# Constants`, `# Registry (Open/Closed extension point)`)
- Architecture notes at module level explaining design constraints (see `frontmatter_core.py` lines 11-20 SOLID principles)

**JSDoc/TSDoc:** Not used (Python project)

**Docstring Format:**
- Preferred: Google-style with clear Args, Returns, Raises sections
- Example from codebase:
  ```python
  def extract_frontmatter(content: str) -> tuple[str | None, int, int]:
      """Extract the YAML frontmatter block from markdown file content.

      Args:
          content: Full file content, potentially starting with '---'.

      Returns:
          Tuple of (frontmatter_text, start_line, end_line).
          Returns (None, 0, 0) if no valid frontmatter block is found.
      """
  ```

## Function Design

**Size:** Functions range from 5-50 lines; complex validators are 100-300+ lines with clear sub-sections
- Small utility functions: `_safe_load_yaml()` (13 lines)
- Medium validator methods: `validate()` (30-80 lines)
- Large complex methods: Complex validators broken into logical sub-functions

**Parameters:**
- Prefer explicit parameters over **kwargs (most functions have <5 params)
- Use type hints consistently (e.g., `path: Path`, `verbose: bool`)
- Optional parameters use `param: Type | None = None`
- Mutable default args avoided; use None guards instead

**Return Values:**
- Single values: `SomeType`
- Multiple related values: Named tuples or dataclasses (e.g., `tuple[str | None, int, int]`)
- Success/failure: Use result dataclasses (`ValidationResult`) not boolean
- Optional: Use `Type | None` instead of raising exceptions for missing data

## Module Design

**Exports:**
- `frontmatter_core.py`: Explicitly exports constants, models, and functions in docstring (lines 22-35)
- `frontmatter_utils.py`: All public functions listed in module docstring (lines 8-12)
- `plugin_validator.py`: Entry point (main function via Typer CLI) plus public validators and result types

**Barrel Files:** Not used; direct imports of needed functions

**Public vs Private:**
- Private: Underscore-prefixed functions and internal dataclasses (e.g., `_PlainCliRunner` in conftest.py)
- Public: Classes/functions without underscore, explicitly documented in module docstrings
- Test helpers: Internal to test modules, no export convention needed

## Type Hints

**Patterns:**
- Use `from __future__ import annotations` for PEP 563 deferred evaluation
- Use `TYPE_CHECKING` blocks for imports only needed by type checkers
- Generic types: `dict[str, Any]`, `list[Path]`, `tuple[str, int]`
- Unions: `str | None` (PEP 604 syntax, requires Python 3.10+)
- Protocols: Used for validator abstraction (see `Validator` Protocol)
- TypeAlias: Explicit for recursive types (e.g., `YamlValue: TypeAlias = dict[str, "YamlValue"] | ...`)

## Dataclass vs Pydantic

**Dataclasses:**
- Used for simple data holders with no validation (e.g., `ValidationIssue`, `ValidationResult`)
- When validation not needed or custom validation logic in separate function

**Pydantic:**
- Used for frontmatter schema validation (SkillFrontmatter, CommandFrontmatter, AgentFrontmatter)
- Provides automatic validation, field aliasing (e.g., `alias="allowed-tools"`), normalization validators
- ConfigDict: Set `extra="allow"` to permit additional fields beyond schema

## Python Version

**Target:** Python 3.11+ (specified in plugin_validator.py line 3: `# requires-python = ">=3.11"`)
- Uses PEP 604 union syntax (`X | None`)
- Uses PEP 563 deferred annotations (`from __future__ import annotations`)
- Uses `StrEnum` from enum module (Python 3.11+)

---

*Convention analysis: 2026-03-02*
