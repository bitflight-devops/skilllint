# Ruff Project Layout Research

**Purpose:** Understand how ruff (a well-engineered Rust linter) separates CLI / core / domain / reporting at the package level, to inform restructuring a 5,700-line Python monolith.
**Researched:** 2026-03-10
**Confidence:** MEDIUM — derived from official contributing docs, DeepWiki analysis, and GitHub directory listings. Cargo.toml dependency layers inferred from contributing docs and crate descriptions; not directly verified against the raw Cargo.toml.

---

## 1. Crate Inventory

The ruff repo is a flat Cargo workspace under `crates/`. As of early 2026 it contains 45+ crates. The key ones grouped by layer:

### Binary / Entry Points

| Crate | Type | Responsibility |
|-------|------|----------------|
| `crates/ruff` | binary | CLI entry point. Parses argv, dispatches to subcommands (`check`, `format`, `server`). Thin wrapper — contains no lint logic. |
| `crates/ruff_dev` | binary | Internal development tooling (`cargo dev generate-all`, rule scaffolding, etc.). Never shipped. |
| `crates/ty` | binary | Entry point for the `ty` type-checker CLI (separate product, same monorepo). |

### Core Engine (library crates)

| Crate | Responsibility |
|-------|---------------|
| `crates/ruff_linter` | Largest crate. Contains **all lint rules**, rule registry, fix applicator, the check-pass runner. The CLI calls into this. |
| `crates/ruff_workspace` | Configuration and settings resolution. Reads `pyproject.toml` / `ruff.toml`, resolves per-file overrides, produces `Settings` objects passed to the linter. |
| `crates/ruff_cache` | On-disk caching of lint results (file hash → diagnostics). Plugged in at the CLI layer to skip unchanged files. |
| `crates/ruff_graph` | Import-graph / dependency analysis for rules that need cross-file context. |

### Formatter (separate subsystem)

| Crate | Responsibility |
|-------|---------------|
| `crates/ruff_python_formatter` | Python-specific formatter. Two-layer design: language-agnostic formatting concerns in `ruff_formatter`, Python-specific IR on top. |
| `crates/ruff_formatter` | Language-agnostic formatting infrastructure (IR, print algorithm, options). Fork of Rome's `rome_formatter`. |

### Language Server

| Crate | Responsibility |
|-------|---------------|
| `crates/ruff_server` | LSP server. Translates LSP requests into linter/formatter calls. Returns diagnostics and code actions to editors. |

### Language / AST Infrastructure

| Crate | Responsibility |
|-------|---------------|
| `crates/ruff_python_parser` | Hand-written recursive descent / Pratt parser. Produces the AST from Python source text. Supports latest Python syntax. |
| `crates/ruff_python_ast` | AST node type definitions and visitor traits. Shared by linter, formatter, semantic analysis. |
| `crates/ruff_python_semantic` | Semantic model: scope analysis, binding resolution, type narrowing hints. Rules that need name resolution call into this. |
| `crates/ruff_python_stdlib` | Typed catalogue of the Python standard library (module names, builtin names, deprecated symbols). Used by rules checking stdlib usage. |
| `crates/ruff_python_trivia` | Utilities for whitespace and comment handling (non-semantic token classification). Used by formatter and some rules. |

### Low-Level Utilities

| Crate | Responsibility |
|-------|---------------|
| `crates/ruff_diagnostics` | Rule-independent diagnostic/fix types. Defines `Diagnostic`, `Fix`, `Edit` structs that rules produce. |
| `crates/ruff_source_file` | Source text representation with line/column index. Shared across parser, linter, formatter. |
| `crates/ruff_text_size` | Byte-offset types (`TextSize`, `TextRange`). Tiny crate; prevents mixing of byte/char offsets. |
| `crates/ruff_index` | Typed index types (newtype wrappers around `u32`) for arena indexing. Avoids `usize` confusion. |
| `crates/ruff_wasm` | Compiles ruff to WebAssembly for the browser-based playground. Exposes a JS API. |

---

## 2. Separation of Concerns at Crate Level

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRY POINT LAYER                                          │
│  crates/ruff (CLI)        crates/ty (type-checker CLI)      │
└─────────────────┬───────────────────────────────────────────┘
                  │ calls into
┌─────────────────▼───────────────────────────────────────────┐
│  COORDINATION LAYER                                         │
│  ruff_workspace (config)  ruff_cache (result caching)       │
│  ruff_server (LSP)                                          │
└────────┬────────────────────────────────────────────────────┘
         │ calls into
┌────────▼────────────────────────────────────────────────────┐
│  ENGINE LAYER                                               │
│  ruff_linter (all rules)  ruff_python_formatter             │
│  ruff_formatter (IR)                                        │
└────────┬────────────────────────────────────────────────────┘
         │ calls into
┌────────▼────────────────────────────────────────────────────┐
│  LANGUAGE LAYER                                             │
│  ruff_python_parser       ruff_python_ast                   │
│  ruff_python_semantic     ruff_python_stdlib                │
│  ruff_python_trivia                                         │
└────────┬────────────────────────────────────────────────────┘
         │ calls into
┌────────▼────────────────────────────────────────────────────┐
│  PRIMITIVE LAYER                                            │
│  ruff_diagnostics         ruff_source_file                  │
│  ruff_text_size           ruff_index                        │
└─────────────────────────────────────────────────────────────┘
```

Key design observations:

- **The CLI crate (`crates/ruff`) is deliberately thin.** It handles argument parsing and calls `ruff_linter` / `ruff_workspace`. No rule logic lives there.
- **All rules are co-located in one crate (`ruff_linter`).** This is a deliberate trade-off: discoverability over maximum decoupling. Each rule is a module; the registry auto-discovers them.
- **The formatter is a separate subsystem**, not baked into the linter. It shares AST types but has its own IR and print algorithm.
- **Semantic analysis is a crate**, not embedded in rules. Rules that need name resolution take a `&SemanticModel` parameter, keeping rule code free of analysis boilerplate.
- **Diagnostics types are at the bottom of the dependency graph.** `ruff_diagnostics` has no dependency on parsing or rules — it only defines the `Diagnostic` and `Fix` output structures.

---

## 3. Python-Facing Package (PyPI)

**Package name on PyPI:** `ruff`

The PyPI `ruff` package is a **native binary wheel**. There is no Python source code in the distribution — the wheel contains only the compiled Rust binary. The `ruff` binary is placed into the wheel's `bin/` (scripts) directory so that `pip install ruff` makes `ruff` available on `PATH`.

Build toolchain: **maturin** (the standard tool for shipping Rust binaries and extensions as Python wheels). maturin handles:
- Cross-compilation for all target triples (win/mac/linux × x86_64/aarch64/etc.)
- Wheel metadata generation
- PyPI upload

The `crates/ruff` binary crate is the only input to the wheel. The other library crates are compiled in statically — there is no runtime Python `import` relationship.

**Takeaway for a Python linter project:** There is no Python ↔ Rust FFI here. The Python package is purely a distribution mechanism for a compiled binary. A Python linter written in Python ships the same way in principle: a wheel with an entry-point script, built by whatever build backend the project uses (hatchling, flit, setuptools).

---

## 4. Workspace Cargo.toml Dependency Layers

The workspace `Cargo.toml` at the repo root:
- Lists all crates under `members = ["crates/*"]`
- Defines workspace-level `[dependencies]` to pin shared library versions across all crates (avoids version drift)
- Uses specialized `[profile.*]` entries: hot-path crates compiled with `codegen-units = 1` for maximum optimisation; dev builds use faster defaults

Inferred dependency graph direction (from contributing docs):

```
ruff  →  ruff_linter, ruff_workspace, ruff_cache, ruff_server, ruff_python_formatter
ruff_linter  →  ruff_python_ast, ruff_python_semantic, ruff_python_stdlib, ruff_diagnostics, ruff_source_file
ruff_python_semantic  →  ruff_python_ast, ruff_python_parser
ruff_python_ast  →  ruff_text_size, ruff_source_file
ruff_diagnostics  →  ruff_text_size
ruff_text_size  →  (no ruff deps)
```

The primitives (`ruff_text_size`, `ruff_index`, `ruff_diagnostics`, `ruff_source_file`) form a foundation layer with no upward dependencies.

---

## 5. Lessons for a Python Package Layout

The ruff architecture maps to a Python package restructuring as follows:

| ruff crate | Python package equivalent |
|------------|--------------------------|
| `crates/ruff` (CLI binary) | `src/agentskills_linter/cli.py` + `__main__.py` — thin, no logic |
| `crates/ruff_workspace` | `src/agentskills_linter/config.py` — settings loading, resolution |
| `crates/ruff_linter` | `src/agentskills_linter/rules/` — all rules as modules, registered centrally |
| `crates/ruff_diagnostics` | `src/agentskills_linter/models.py` — `Diagnostic`, `Fix`, `Severity` dataclasses |
| `crates/ruff_python_ast` + `ruff_python_parser` | `src/agentskills_linter/parsing.py` — AST wrappers, visitor utilities |
| `crates/ruff_python_semantic` | `src/agentskills_linter/semantic.py` — scope/binding analysis |
| `crates/ruff_cache` | `src/agentskills_linter/cache.py` — result caching |
| `crates/ruff_server` | `src/agentskills_linter/lsp.py` or separate package |
| `crates/ruff_dev` | `scripts/` or `tools/` — never imported by the main package |

**Critical structural rules to copy from ruff:**

1. **Diagnostics / output models have no dependencies on rules or parsing.** Define them first; everything else imports from them.
2. **The CLI imports from the engine; the engine never imports from the CLI.** Dependency direction is one-way.
3. **Rules are modules, not classes scattered across files.** One module per rule, auto-discovered by the registry.
4. **Configuration resolution is isolated.** No rule accesses `sys.argv` or reads config files directly; it receives a `Settings` object.
5. **Semantic analysis is injected, not embedded.** Rules receive a pre-built semantic context, not raw AST.

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Crate inventory (names) | MEDIUM-HIGH | Official contributing docs + GitHub directory listings |
| Crate responsibilities | MEDIUM | Official contributing docs + DeepWiki analysis |
| Dependency layer ordering | MEDIUM | Inferred from contributing docs; Cargo.toml not directly read |
| PyPI / wheel distribution | HIGH | PyPI page + maturin docs are authoritative |
| Mapping to Python layout | MEDIUM | Structural analogy; not verified against ruff source directly |

---

## Sources

- [Contributing | Ruff — official crate descriptions](https://docs.astral.sh/ruff/contributing/)
- [ruff/crates at main · astral-sh/ruff](https://github.com/astral-sh/ruff/tree/main/crates)
- [ruff/Cargo.toml at main](https://github.com/astral-sh/ruff/blob/main/Cargo.toml)
- [astral-sh/ruff | DeepWiki — architecture overview](https://deepwiki.com/astral-sh/ruff)
- [Language Server Architecture | DeepWiki](https://deepwiki.com/astral-sh/ruff/7.1-language-server-architecture)
- [ruff · PyPI](https://pypi.org/project/ruff/)
- [ruff/crates/ruff_server/CONTRIBUTING.md](https://github.com/astral-sh/ruff/blob/main/crates/ruff_server/CONTRIBUTING.md)
