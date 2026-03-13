# Code Smell Report: benchmark.yml

**File**: `/home/user/agentskills-linter/.github/workflows/benchmark.yml`
**Date**: 2026-03-13T05:45:39Z

## Issues Found

### SMELL-1: Inline Python script in CI workflow [HIGH]

**Location**: Lines 136-175 ("Compute and print performance ratio" step)

A 39-line Python script is embedded inline in a `run:` block using a heredoc:

```yaml
- name: Compute and print performance ratio
  run: |
    uv run python - <<'EOF'
    import json, pathlib, sys
    # ... 35 more lines of Python ...
    EOF
```

This inline script:
- Cannot be tested independently
- Cannot be linted or type-checked by CI tooling (ruff, mypy ignore heredocs)
- Cannot be reused outside the workflow
- Is harder to review in PRs (YAML + Python mixed context)

**Fix**: Extract to `scripts/bench_ratio.py` and call it from the workflow:
```yaml
- name: Compute and print performance ratio
  run: |
    source .venv/bin/activate
    python scripts/bench_ratio.py \
      --compare scripts/results/benchmark_results.json \
      --base scripts/results/benchmark_results_base.json
```

### SMELL-2: Copy-paste duplication in I/O benchmark steps [MEDIUM]

**Location**: Lines 62-72 ("Run bench_io for github-action-benchmark output") vs Lines 116-123 ("Run base I/O benchmark")

Both steps contain nearly identical shell blocks:
```bash
set -o pipefail
source .venv/bin/activate
# ... resolve bench_io.py path ...
python "$BENCH_IO" /tmp/bench-plugin --output <output_file> | tee <results_file>
```

The second block adds a fallback to `/tmp/bench_io.py` (from the "Preserve" step), but the core pattern is duplicated.

**Fix**: Create a small wrapper script `scripts/run_bench_io.sh` that accepts output paths as arguments and handles the bench_io.py fallback logic. Or, consolidate the bench_io invocation into `bench_io.py` itself with a `--base-fallback` flag.

### SMELL-3: Fragile file-preservation hack across checkout [MEDIUM]

**Location**: Lines 95-100 ("Preserve bench_io.py before base-ref checkout") and Lines 119-121 (fallback logic)

The workflow copies `bench_io.py` to `/tmp/` before checking out the base ref, then uses a fallback `if [ ! -f "$BENCH_IO" ]; then BENCH_IO=/tmp/bench_io.py`. This is a leaky abstraction -- the CI workflow is managing script portability across git checkouts rather than using a proper mechanism (e.g., a pinned action, or running benchmarks in separate jobs with artifact passing).

**Impact**: If `bench_io.py`'s interface changes between branches, the preserved copy may be incompatible with the base ref's codebase. The fallback silently uses a script from a different commit.

**Fix**: Run base and compare benchmarks in separate jobs that each check out their own ref. Pass results via `actions/upload-artifact` / `actions/download-artifact` and compare in a final job.

## Summary

| Priority | Count |
|----------|-------|
| HIGH     | 1     |
| MEDIUM   | 2     |
