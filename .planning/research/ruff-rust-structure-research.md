# Ruff Rust Rule Organization: Structural Reference

**Researched:** 2026-03-10
**Confidence:** MEDIUM-HIGH — directory hierarchy and file patterns confirmed via actual GitHub file paths present in search results and CONTRIBUTING.md citations. `codes.rs` registry detail confirmed via DeepWiki analysis of the repo. No direct file reads (WebFetch blocked); all claims traceable to specific cited sources.

---

## 1. Top-Level Directory Hierarchy

```
crates/ruff_linter/src/
    rules/                          ← all lint rules live here
        <category>/                 ← one directory per linter family
            mod.rs                  ← category module: re-exports + tests
            rules/                  ← one file per rule
                <rule_name>.rs
                <rule_name>.rs
                ...
            snapshots/              ← insta snapshot files for tests
                ruff_linter__rules__<category>__tests__<RuleName>__<fixture>.snap
        <category>/
            ...
    codes.rs                        ← Rule enum + RuleGroup enum + code mapping
    registry.rs                     ← Rule trait, RuleNamespace, selector logic
    checkers/
        ast/
            analyze/
                statement.rs        ← AST visitor dispatch for statement rules
                expression.rs       ← AST visitor dispatch for expression rules

crates/ruff_linter/resources/
    test/
        fixtures/
            <category>/             ← Python test files (one per rule, e.g. F401.py)
```

**Source:** Confirmed via actual GitHub file path URLs returned in search results:
- `crates/ruff_linter/src/rules/flake8_bandit/rules/hardcoded_tmp_directory.rs`
- `crates/ruff_linter/src/rules/flake8_use_pathlib/rules/os_makedirs.rs`
- `crates/ruff_linter/src/rules/pydocstyle/rules/not_empty.rs`
- `crates/ruff_linter/src/rules/pyflakes/rules/unused_import.rs`
- `crates/ruff_linter/src/rules/pyupgrade/rules/f_strings.rs`
- `crates/ruff_linter/src/rules/tryceratops/rules/try_consider_else.rs`
- `crates/ruff_linter/src/rules/refurb/rules/fstring_number_format.rs`
- `crates/ruff_linter/src/rules/flake8_bugbear/mod.rs` (tests confirmed here)

---

## 2. Known Category Directories

These are confirmed or strongly evidenced from search result file paths and rule code documentation:

| Directory | Rule Prefix | Source |
|---|---|---|
| `pyflakes/` | F | Confirmed GitHub path |
| `pycodestyle/` | E, W | Documented in ruff rules page |
| `pylint/` | PL | Documented in ruff rules page |
| `isort/` | I | Documented in ruff rules page |
| `pydocstyle/` | D | Confirmed GitHub path |
| `pyupgrade/` | UP | Confirmed GitHub path |
| `flake8_bugbear/` | B | Confirmed GitHub path (mod.rs) |
| `flake8_bandit/` | S | Confirmed GitHub path |
| `flake8_use_pathlib/` | PTH | Confirmed GitHub path |
| `refurb/` | FURB | Confirmed GitHub path |
| `tryceratops/` | TRY | Confirmed GitHub path |
| `pep8_naming/` | N | Documented in ruff rules page |
| `flake8_comprehensions/` | C4 | Documented in ruff rules page |
| `flake8_print/` | T20 | Documented in ruff rules page |
| `flake8_pytest_style/` | PT | Documented in ruff rules page |
| `mccabe/` | C | Documented in ruff rules page |
| `perflint/` | PERF | Documented in ruff rules page |

This list is not exhaustive — ruff has 50+ linter families. The pattern holds uniformly across all of them.

---

## 3. The `<category>/mod.rs` File

The `mod.rs` in each category directory serves two purposes:

**a) Re-exports all rule modules from the `rules/` subdirectory:**
```rust
// Example: crates/ruff_linter/src/rules/flake8_bugbear/mod.rs
pub(crate) mod rules;
```

**b) Defines all tests for the category:**
```rust
#[cfg(test)]
mod tests {
    use std::path::Path;
    use anyhow::Result;
    use test_case::test_case;
    use crate::registry::Rule;
    use crate::test::test_path;

    #[test_case(Rule::AssertFalse, Path::new("B011.py"); "B011")]
    #[test_case(Rule::AssertRaisesException, Path::new("B017.py"); "B017")]
    // ... one test_case per rule
    fn rules(rule_code: Rule, path: &Path) -> Result<()> {
        let snapshot = format!("{}_{}",
            rule_code.noqa_code(),
            path.to_string_lossy()
        );
        let diagnostics = test_path(
            Path::new("flake8_bugbear").join(path).as_path(),
            &Settings::for_rule(rule_code),
        )?;
        assert_yaml_snapshot!(snapshot, diagnostics);
        Ok(())
    }
}
```

**Key point:** Tests are collected in `mod.rs`, not in the individual rule files. Each test references a fixture file in `resources/test/fixtures/<category>/` and produces a snapshot.

**Source:** CONTRIBUTING.md via docs.astral.sh/ruff/contributing/ (confirmed: "Add the test to the relevant `crates/ruff_linter/src/rules/[linter]/mod.rs` file")

---

## 4. Individual Rule File Anatomy

Each rule file in `rules/<rule_name>.rs` contains all of: the violation type, its message/metadata, the fix logic (if any), and the checker invocation logic. **Tests do NOT live in the rule file** — they live in `mod.rs`.

### Structure of a single rule file:

```rust
// 1. VIOLATION TYPE — annotated with the #[violation] macro
//    This generates: rule name, message, fix availability metadata
use ruff_macros::{ViolationMetadata, derive_message_formats};

#[derive(ViolationMetadata)]
pub(crate) struct HardcodedTmpDirectory {
    pub(crate) path: String,
}

impl Violation for HardcodedTmpDirectory {
    #[derive_message_formats]
    fn message(&self) -> String {
        format!("Use of hardcoded temp directory `{}`", self.path)
    }
    // Optional: fix description if rule has an autofix
    fn fix_title(&self) -> Option<String> {
        Some("Replace with `tempfile.mkstemp()`".to_string())
    }
}

// 2. CHECKER FUNCTION — called by the AST visitor dispatcher
//    Takes an AST node, returns nothing; emits via checker.diagnostics
pub(crate) fn hardcoded_tmp_directory(
    checker: &mut Checker,
    expr: &Expr,
) {
    // ... analyze AST node
    if let Some(violation) = detect_violation(expr) {
        let mut diagnostic = Diagnostic::new(
            HardcodedTmpDirectory { path: violation.path },
            expr.range(),
        );
        // 3. FIX LOGIC — optional, attached to the diagnostic
        if checker.enabled(Rule::HardcodedTmpDirectory) {
            diagnostic.set_fix(Fix::safe_edit(Edit::range_replacement(
                "tempfile.mkstemp()".to_string(),
                expr.range(),
            )));
        }
        checker.diagnostics.push(diagnostic);
    }
}
```

### What lives in the rule file:
- The violation struct (implements `Violation` trait)
- Human-readable message and fix title
- The checker function (pure logic, no I/O)
- Fix construction (if the rule supports autofix)

### What does NOT live in the rule file:
- Tests (→ `mod.rs`)
- Test fixtures (→ `resources/test/fixtures/<category>/`)
- Snapshots (→ `snapshots/` subdirectory)
- Rule code mapping (→ `codes.rs`)
- AST visitor dispatch (→ `checkers/ast/analyze/`)

**Source:** CONTRIBUTING.md cited at docs.astral.sh/ruff/contributing/ and confirmed file path `crates/ruff_linter/src/rules/flake8_bandit/rules/hardcoded_tmp_directory.rs`

---

## 5. Registry: `codes.rs` and `registry.rs`

### `crates/ruff_linter/src/codes.rs`

This is the central registry. It:

1. Defines the `RuleGroup` enum with four states:
   ```rust
   pub enum RuleGroup {
       Stable,
       Preview,
       Deprecated,
       Removed,
   }
   ```

2. Defines the `Rule` enum — **auto-generated** — containing every rule as a variant (one per rule file).

3. Defines the code-to-rule mapping using a proc macro:
   ```rust
   #[ruff_macros::map_codes]
   pub fn code_to_rule(linter: Linter, code: &str) -> Option<(RuleGroup, Rule)> {
       // macro generates match arms at compile time
       // e.g.: (Linter::Pyflakes, "401") => (RuleGroup::Stable, Rule::UnusedImport)
   }
   ```

This macro reads rule implementations at compile time and generates the full mapping. Adding a rule file to `rules/<category>/rules/` and mapping it in `codes.rs` is the registration step.

### `crates/ruff_linter/src/registry.rs`

Contains:
- The `Rule` trait definition
- `RuleNamespace` — maps linter prefixes to `Linter` enum variants
- Selector logic — how rule codes like `F401`, `F`, `ALL` resolve to `Rule` sets

**Source:** DeepWiki analysis at deepwiki.com/astral-sh/ruff/4.1-rule-registry-and-selection (confirmed: "The Rule enum is auto-generated with all rule variants, and the `code_to_rule()` function provides the mapping from linter family and code to `(RuleGroup, Rule)` tuples through the `#[ruff_macros::map_codes]` attribute which generates the full mapping at compile time")

---

## 6. How the Checker Dispatcher Works

Rules are not self-registering AST visitors. Instead, a central AST visitor (`Checker` in `checkers/ast/`) walks the Python AST and calls rule checker functions at each node type:

```
checkers/ast/analyze/
    statement.rs    ← calls rule functions for Import, FunctionDef, etc.
    expression.rs   ← calls rule functions for Call, Constant, etc.
```

Each rule file exports a single checker function. The dispatcher in `statement.rs` or `expression.rs` calls that function when visiting the relevant AST node, IF that rule is enabled in the current configuration.

**Source:** CONTRIBUTING.md: "you'll likely want to augment the logic in `crates/ruff_linter/src/checkers/ast.rs` to call your new function at the appropriate time"

---

## 7. Test Infrastructure Summary

| Artifact | Location | Purpose |
|---|---|---|
| Fixture `.py` file | `resources/test/fixtures/<category>/<RuleCode>.py` | Python code with violations and non-violations |
| Test registration | `rules/<category>/mod.rs` | `#[test_case]` macro per rule |
| Snapshot file | `rules/<category>/snapshots/*.snap` | Expected output (insta crate) |
| Snapshot workflow | `cargo test` → fail → `cargo insta review` → commit | Review-and-accept cycle |

One fixture file per rule. One snapshot per rule. Tests in `mod.rs` wire them together.

---

## 8. Python Analogue Mapping

The goal is to apply these structural patterns to Python. The mapping:

| Ruff (Rust) | Python equivalent |
|---|---|
| `rules/<category>/` | `validators/<domain>/` |
| `rules/<category>/mod.rs` | `validators/<domain>/__init__.py` |
| `rules/<category>/rules/<rule>.rs` | `validators/<domain>/<rule>.py` |
| `rules/<category>/snapshots/` | `tests/snapshots/<domain>/` or pytest parametrize |
| `codes.rs` Rule enum | `validators/__init__.py` ALL_VALIDATORS list |
| `codes.rs` code_to_rule() | `registry.py` or validator `__init__.py` |
| `checkers/ast/analyze/` | `runner.py` dispatch loop |
| `Violation` struct | `Violation` dataclass in `models.py` |
| `#[violation]` macro metadata | `@dataclass` + class docstring = rule description |

**Key structural insight for the Python refactor:**

Ruff's one-file-per-rule pattern achieves maximum isolation at the cost of ~50 files for ~50 rules. For 8-12 validators, grouped-per-domain (pylint pattern) is the correct analogue: one Python file per semantic domain, each file exporting 1-3 validator classes. The `mod.rs`-as-test-hub pattern maps directly: tests live in `tests/test_<domain>.py`, not inline in the validator files.

---

## 9. Confidence Assessment

| Claim | Confidence | Basis |
|---|---|---|
| `rules/<category>/rules/<rule>.rs` hierarchy | HIGH | 8 distinct GitHub file paths confirmed in search results |
| `mod.rs` holds tests, not rule files | HIGH | CONTRIBUTING.md citation confirmed |
| `codes.rs` holds Rule enum + code_to_rule() | HIGH | DeepWiki analysis + CONTRIBUTING.md ("Map the violation struct to a rule code in codes.rs") |
| `#[ruff_macros::map_codes]` generates mapping at compile time | MEDIUM | DeepWiki analysis; macro name confirmed but exact syntax not directly read |
| `snapshots/` directory in each category | HIGH | Fossies snapshot paths confirm: `crates/ruff_linter/src/rules/pyflakes/snapshots/...` |
| `resources/test/fixtures/<category>/` for `.py` fixtures | HIGH | CONTRIBUTING.md citation confirmed |
| RuleGroup enum has Stable/Preview/Deprecated/Removed | HIGH | Multiple sources agree |
| Full category directory list (50+) | MEDIUM | Rule prefix table confirmed; not all directory names directly verified |

---

## Sources

- [ruff CONTRIBUTING.md](https://docs.astral.sh/ruff/contributing/) — "Adding a new rule" section
- [ruff GitHub: flake8_bandit rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/flake8_bandit/rules/hardcoded_tmp_directory.rs)
- [ruff GitHub: flake8_use_pathlib rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/flake8_use_pathlib/rules/os_makedirs.rs)
- [ruff GitHub: pydocstyle rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/pydocstyle/rules/not_empty.rs)
- [ruff GitHub: pyflakes rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/pyflakes/rules/unused_import.rs)
- [ruff GitHub: pyupgrade rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/pyupgrade/rules/f_strings.rs)
- [ruff GitHub: refurb rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/refurb/rules/fstring_number_format.rs)
- [ruff GitHub: tryceratops rule file](https://github.com/astral-sh/ruff/blob/main/crates/ruff_linter/src/rules/tryceratops/rules/try_consider_else.rs)
- [DeepWiki: Rule Registry and Selection](https://deepwiki.com/astral-sh/ruff/4.1-rule-registry-and-selection)
- [DeepWiki: Example Rule Implementation](https://deepwiki.com/astral-sh/ruff/4.3-example-rule-implementation)
- [DeepWiki: Testing Infrastructure](https://deepwiki.com/astral-sh/ruff/9.2-adding-rules-and-features)
- [ruff Rules page](https://docs.astral.sh/ruff/rules/)
- [Fossies pyflakes snapshot](https://fossies.org/linux/ruff/crates/ruff_linter/src/rules/pyflakes/snapshots/ruff_linter__rules__pyflakes__tests__preview__F401_F401_25__all____init__.py.snap)
