# Modernization Report: bench_io.py

**File**: `/home/user/agentskills-linter/scripts/bench_io.py`
**Date**: 2026-03-13T05:45:39Z
**Target**: Python >=3.11

## Assessment

The file already uses modern Python patterns throughout. No legacy typing imports.

## Potential Modernizations

### MOD-1: Replace `os.walk` with `Path.rglob` in `_count_files` [LOW]

```python
# Current (line 34)
for _root, _dirs, files in os.walk(directory):
    count += len(files)

# Modern
return sum(1 for p in directory.rglob("*") if p.is_file())
```

This also eliminates the `import os` dependency.

### MOD-2: Use `TypedDict` for benchmark result shape [LOW]

Same as bench_cpu.py -- `dict[str, float | int]` return type on `run_benchmark` (line 66) would benefit from a `TypedDict`.
