# Modernization Report: bench_cpu.py

**File**: `/home/user/agentskills-linter/scripts/bench_cpu.py`
**Date**: 2026-03-13T05:45:39Z
**Target**: Python >=3.11

## Assessment

The file already uses modern Python patterns:
- `from __future__ import annotations` (line 16)
- Native generic syntax `dict[str, float]`, `list[dict[str, float | str]]` (lines 58, 118)
- `Path` from pathlib for file operations (line 21)
- Pipe union `Path | None` (line 145)

## Potential Modernizations

### MOD-1: Use `TypedDict` for benchmark result shape [LOW]

The return type `dict[str, float]` on `_run_cpu_benchmark` (line 58) loses key information. A `TypedDict` would make the `mean_ms`/`total_ms` contract explicit:

```python
from typing import TypedDict

class CpuTiming(TypedDict):
    mean_ms: float
    total_ms: float
```

### MOD-2: No other modernization opportunities identified

The file is already well-typed and uses modern constructs. No legacy `typing` imports, no `Optional`/`Union`, no `List`/`Dict`.
