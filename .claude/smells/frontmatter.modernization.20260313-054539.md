# Modernization Report: frontmatter.py

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`
**Date**: 2026-03-13T05:45:39Z
**Target**: Python >=3.11

## Assessment

The file uses `from __future__ import annotations` and modern union syntax. However, it has larger structural issues (stub code) that take priority over modernization.

## Potential Modernizations

### MOD-1: Accept `Path | str` instead of bare `str` for `file_path` parameter [MEDIUM]

`process_markdown_file(file_path: str)` (line 18) accepts only `str` but constructs `pathlib.Path(file_path)` internally. Modern API should accept `Path | str` and normalize once:

```python
def process_markdown_file(file_path: Path | str) -> None:
    path = Path(file_path)
    # use path everywhere
```

### MOD-2: Use `Path` throughout instead of string concatenation [MEDIUM]

Line 57 uses string concatenation for temp path: `temp_path = file_path + ".tmp"`. This breaks if `file_path` is a `Path` object. Should use:

```python
temp_path = path.with_suffix(path.suffix + ".tmp")
```

### MOD-3: Consider `NamedTuple` or dataclass for `lint_and_fix` return [LOW]

`tuple[bool, bytes | None]` is a positional return type. A `NamedTuple` would improve readability:

```python
class LintResult(NamedTuple):
    needs_fix: bool
    fixed_bytes: bytes | None
```
