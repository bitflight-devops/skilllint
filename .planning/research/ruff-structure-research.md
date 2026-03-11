# Ruff Structure Research: Python Linter Package Design Reference

**Researched:** 2026-03-10
**Confidence:** MEDIUM — ruff internals are Rust; Python-facing layer verified via PyPI/docs. Pylint/flake8 patterns verified via GitHub source URLs. Textbook CLI layout patterns verified via Python Packaging Authority docs.

---

## 1. Ruff's Python-Facing Package: What the pip Install Actually Contains

**Finding:** The `ruff` pip package is a near-empty Python shim. It contains no rules, no validators, no reporters written in Python.

The package ships a platform-specific pre-compiled Rust binary. The Python files (`ruff/__init__.py`, `ruff/__main__.py`) contain only a thin launcher that calls `os.spawnv()` (or equivalent) to exec the binary with forwarded arguments and return its exit code.

**Implication for this project:** Ruff is not a usable design reference for Python module layout because its Python layer has zero domain logic. It is intentionally a binary wrapper.

**Source confidence:** MEDIUM — confirmed by PyPI package description and community documentation; not verified against the raw `__init__.py` source (WebFetch blocked).

**Sources:**
- https://pypi.org/project/ruff/
- https://realpython.com/ref/tools/ruff/

---

## 2. Ruff's Internal Rust Architecture (for conceptual reference only)

Even though the Rust internals are not directly reusable in Python, the structural concepts are instructive:

| Crate | Purpose | Python analogue |
|---|---|---|
| `crates/ruff` | Thin CLI binary, arg parsing only | `cli.py` / `__main__.py` |
| `crates/ruff_linter` | All lint rules and core logic | `validators/` + `rules/` |
| `crates/ruff_workspace` | Settings/config resolution | `config.py` / `models.py` |
| `crates/ruff_cache` | Result caching | `cache.py` |

**Key structural decision in ruff:** Every lint rule lives in `crates/ruff_linter/src/rules/<category>/rules/<rule_name>.rs` — **one file per rule**, grouped into category subdirectories (e.g., `pyflakes/`, `pylint/`, `flake8_bugbear/`). This is the most granular pattern possible.

**Source:** https://docs.astral.sh/ruff/contributing/ and https://github.com/astral-sh/ruff/tree/main/crates/ruff_linter/src

---

## 3. Flake8: Python Linter with Explicit Module Separation

Flake8 is a pure-Python linter and the most instructive reference for this project. Its `src/flake8/` layout:

```
src/flake8/
    api/
        legacy.py           # Public Python API
    checker.py              # Core checking orchestration
    formatting/
        base.py             # Abstract reporter/formatter base
        default.py          # Default output formatter
    main/
        application.py      # App lifecycle (init, run, teardown)
        cli.py              # Thin CLI entry point
        options.py          # Option registration at startup
    options/
        aggregator.py       # Merges CLI + config options
        config.py           # Config file discovery and parsing
        manager.py          # Option manager (add/get options)
    plugins/
        finder.py           # Plugin discovery via entry_points
    processor.py            # Per-file processing pipeline
```

**Key structural decisions:**

1. **Thin CLI (`main/cli.py`):** Only creates `Application`, calls `run()`, exits. No logic.
2. **Application class (`main/application.py`):** Owns the lifecycle. Wires together options, plugins, checkers, formatters.
3. **Formatters/reporters are separate from checkers:** `formatting/` is completely decoupled from `checker.py`. The formatter receives result objects; it does not know about rule internals.
4. **Rules are not in flake8 itself:** Flake8 delegates rules to plugins (`pycodestyle`, `pyflakes`, `mccabe`). Each plugin registers checker classes via `entry_points`. There is no `rules/` directory in flake8 core.
5. **Options are a first-class subsystem:** Three-layer options (`aggregator` → `manager` → `config`) keeps CLI parsing, config file parsing, and option registration separated.

**Source:** https://flake8.pycqa.org/en/stable/_modules/index.html and https://github.com/PyCQA/flake8

---

## 4. Pylint: Grouped-Rules-Per-File Pattern

Pylint uses **grouped rules per file** — the middle-ground pattern between one-file-per-rule and all-rules-in-one-file.

```
pylint/
    checkers/
        base/
            basic_checker.py     # ~10 basic code rules grouped
            __init__.py
        imports.py               # All import-related rules
        classes.py               # All class-related rules
        exceptions.py            # All exception-related rules
        format.py                # All formatting/style rules
        typecheck.py             # All type-checking rules
        variables.py             # All variable-scope rules
        ...
    reporters/
        text.py                  # Text output reporter
        json.py                  # JSON reporter
        junit.py                 # JUnit XML reporter
    lint/
        pylinter.py              # Core linting orchestration
        message_store.py         # Rule message registry
    message/
        message.py               # Message model/data class
        message_definition.py    # Rule metadata
```

**Key structural decisions:**

1. **Grouped-rules-per-file:** Each file in `checkers/` owns a semantic domain (imports, classes, variables). A checker file typically contains 1-3 `BaseChecker` subclasses covering related rules.
2. **BaseChecker pattern:** Every rule group inherits from `BaseChecker`. Rules are declared as class-level `msgs` dicts (rule ID → message definition), not as separate objects or files.
3. **Reporters are a parallel subsystem:** `reporters/` is entirely separate from `checkers/`. Reporters receive `Message` objects; they are blind to how rules are implemented.
4. **Message as the domain model:** `Message` and `MessageDefinition` are the central data transfer objects between the checker subsystem and the reporter subsystem.

**Source:** https://github.com/pylint-dev/pylint/tree/main/pylint/checkers and https://pylint.pycqa.org/en/latest/development_guide/how_tos/custom_checkers.html

---

## 5. Rule Granularity: Three Patterns Compared

| Pattern | Used by | Pro | Con |
|---|---|---|---|
| One file per rule | ruff (Rust) | Maximum isolation, easy to find/add/delete rules | Many files, more boilerplate per rule |
| Grouped rules per file | pylint, pyright checkers | Balances findability with file count | Rules in same file share fate; harder to isolate |
| All rules in one file | Small/custom linters | Simple for <10 rules | Unmanageable at scale |

**Recommendation for this project (8-12 validators):** Use **grouped-rules-per-file** (pylint pattern). One file per validator class is appropriate at this scale. If validators share a base class and related concerns, 2-3 per file is acceptable. Do not use one-file-per-rule unless rules number >20.

---

## 6. Textbook Python Package Layout for a CLI Linter with 8-12 Validators

Based on flake8, pylint, and Python Packaging Authority guidance, the following layout is the established standard:

```
src/
  agentskills_linter/
      __init__.py               # Package version only
      __main__.py               # python -m entry: calls cli.main()
      cli.py                    # Thin: argparse/click setup, calls runner
      runner.py                 # Orchestration: wires models→validators→reporters
      models.py                 # Data classes: SkillFile, Violation, CheckResult
      config.py                 # Config loading and resolution
      validators/
          __init__.py           # Exports: ALL_VALIDATORS list
          base.py               # BaseValidator ABC
          skill_metadata.py     # Validator: skill metadata rules
          tool_definitions.py   # Validator: tool definition rules
          prompt_structure.py   # Validator: prompt/instruction rules
          ...                   # One file per semantic domain
      reporters/
          __init__.py           # Exports: get_reporter(format)
          base.py               # BaseReporter ABC
          text.py               # Human-readable output
          json.py               # Machine-readable output
          github.py             # GitHub Actions annotation format
      integrations/             # Platform-specific I/O adapters
          __init__.py
          claude_code.py
          ...

tests/
  unit/
  integration/

pyproject.toml                  # [project.scripts] entry_points here
```

**Entry point registration (pyproject.toml):**
```toml
[project.scripts]
agentskills-lint = "agentskills_linter.cli:main"
```

**CLI stays thin — example `cli.py` shape:**
```python
def main() -> None:
    args = parse_args()
    config = load_config(args)
    violations = run(config)           # delegates to runner.py
    report(violations, config.format)  # delegates to reporters/
    raise SystemExit(1 if violations else 0)
```

**Source:** https://packaging.python.org/en/latest/guides/creating-command-line-tools/ and https://realpython.com/python-application-layouts/

---

## 7. Key Architectural Rules from the Reference Ecosystem

1. **CLI entry point contains zero domain logic.** It parses arguments, delegates, exits. If `cli.py` imports from `validators/` directly, something is wrong.

2. **Reporters are blind to rule internals.** The reporter receives a list of `Violation` (or equivalent) data objects. It does not call validators or know how violations were produced.

3. **Validators are blind to output format.** Validators return violations; they never print or format output.

4. **Models are the shared interface.** `models.py` (or equivalent) defines the data classes that validators produce and reporters consume. Both subsystems import from models; models import from neither.

5. **`__init__.py` at the validators/ level exposes a registration list**, e.g. `ALL_VALIDATORS = [SkillMetadataValidator, ToolDefinitionValidator, ...]`. The runner imports this list, not individual validator modules. This is the pylint pattern (`register()` function in each checker module).

6. **Config resolution is a separate concern.** Do not mix config loading into the CLI or validators. A `config.py` or `config/` subpackage resolves precedence: CLI args > config file > defaults.

---

## 8. Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Ruff Python package is a shim | MEDIUM | PyPI docs + community sources; source not directly read |
| Ruff Rust rule-per-file pattern | MEDIUM | Contributing docs + repo tree URLs |
| Flake8 module layout | HIGH | Official module index at flake8.pycqa.org lists exact submodule paths |
| Pylint grouped-rules-per-file | HIGH | GitHub source tree URLs confirm checker file names |
| Textbook CLI layout | HIGH | Python Packaging Authority + Real Python application layouts |

---

## Sources

- [ruff PyPI](https://pypi.org/project/ruff/)
- [ruff Contributing Guide](https://docs.astral.sh/ruff/contributing/)
- [flake8 Module Index](https://flake8.pycqa.org/en/stable/_modules/index.html)
- [flake8 GitHub](https://github.com/PyCQA/flake8)
- [pylint checkers tree](https://github.com/pylint-dev/pylint/tree/main/pylint/checkers)
- [pylint custom checkers guide](https://pylint.pycqa.org/en/latest/development_guide/how_tos/custom_checkers.html)
- [Python Packaging: Creating CLI Tools](https://packaging.python.org/en/latest/guides/creating-command-line-tools/)
- [Real Python: Python Application Layouts](https://realpython.com/python-application-layouts/)
- [Entry Points Specification](https://packaging.python.org/en/latest/specifications/entry-points/)
