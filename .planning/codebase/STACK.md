# Technology Stack

**Analysis Date:** 2026-03-02

## Languages

**Primary:**
- Python 3.11+ - Main implementation language for skilllint validator and related scripts

## Runtime

**Environment:**
- Python 3.11+

**Package Manager:**
- `uv` - Modern Python package and script runner
- Lockfile: Not detected (uses PEP 723 inline dependencies)

## Frameworks

**Core:**
- Typer 0.21.0+ - CLI framework for plugin-validator and auto_sync_manifests, provides Typer.testing.CliRunner
- Pydantic 2.0.0+ - Data validation framework for frontmatter schema models
- python-frontmatter 1.1.0+ - YAML frontmatter extraction and manipulation
- ruamel.yaml 0.18.0+ - Round-trip YAML parsing and serialization

**Token Counting:**
- tiktoken 0.8.0+ - OpenAI token encoder for token-based complexity measurement

**Git Integration:**
- GitPython 3.1.45+ - Git repository interaction via Repo, entry_key, and exception handling

**Terminal UI:**
- Rich - Terminal rendering with colors, panels, formatting (imported in plugin_validator.py)

**Testing:**
- pytest - Test framework for skilllint test suite
- pytest fixtures for CLI testing via Typer.testing.CliRunner

## Key Dependencies

**Critical:**
- Pydantic - Core validation system for all frontmatter types (SkillFrontmatter, CommandFrontmatter, AgentFrontmatter)
- Typer - CLI layer for both plugin_validator.py and auto_sync_manifests.py entry points
- tiktoken - Required for token-based complexity validation (SK006/SK007 error checks)
- GitPython - Required for git repository operations in plugin_validator and auto_sync_manifests

**Infrastructure:**
- python-frontmatter - Handles YAML/markdown separation with custom RuamelYAMLHandler
- ruamel.yaml - Preserves YAML formatting on round-trip operations (quotes only when required)
- Rich - Terminal output formatting and ANSI color/styling

## Configuration

**Environment:**
- PEP 723 script metadata - Dependencies declared inline in shebang scripts:
  - `plugin_validator.py`: requires-python >=3.11, all dependencies declared in /// script block
  - `auto_sync_manifests.py`: Standalone script, uses stdlib + git/subprocess
  - `frontmatter_core.py`: Plain library module (not a PEP 723 script), no inline metadata
  - `frontmatter_utils.py`: Plain library module (not a PEP 723 script), no inline metadata

**Build:**
- No build configuration files detected at root (no setup.py, pyproject.toml, or build manifests in main directory)
- Package appears to be distributed as standalone Python scripts executable via `uv run`

**Runtime Configuration:**
- Environment variable `CLAUDECODE` - Detects if running inside Claude Code environment
- Environment variable `CLAUDE_CODE_REMOTE` - Detects remote mode
- Environment variable `CLAUDE_CODE_GIT_BASH_PATH` - Stores resolved git-bash path on Windows (set by _git_bash_path())
- Environment variable `LOCALAPPDATA` - Used on Windows to find git-bash installation path
- Environment variable `NO_COLOR` - Controls Rich terminal color output (standard NO_COLOR convention)

## Platform Requirements

**Development:**
- Python 3.11+ interpreter
- Git 2.x+ (required for GitPython and git operations)
- npm/npx (used by auto_sync_manifests.py for prettier formatting, resolved via shutil.which("npx"))

**Production:**
- Python 3.11+
- Git 2.x+
- Optional: npx for manifest formatting

**Windows-Specific:**
- git-bash executable (resolved from PATH or LOCALAPPDATA\Programs\Git)

---

*Stack analysis: 2026-03-02*
