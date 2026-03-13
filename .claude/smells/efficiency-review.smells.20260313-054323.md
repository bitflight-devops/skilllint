# Efficiency Code Smell Report

**Date**: 2026-03-13T05:43:23Z
**Files Reviewed**: 6
**Focus**: Redundant computation, TOCTOU, memory safety, parallelism opportunities

---

## HIGH Priority

### 1. Duplicated benchmark logic in `test_cpu_linting_large_yaml()` (bench_cpu.py:90-115)

**File**: `/home/user/agentskills-linter/scripts/bench_cpu.py`
**Lines**: 90-115

The test function `test_cpu_linting_large_yaml()` manually rebuilds the document via `_build_large_yaml_document()` and re-runs the entire timing loop (lines 97-105), duplicating the logic already encapsulated in `_run_cpu_benchmark()` (lines 58-87). The only difference is the test prints output and raises `AssertionError` on timeout, while `_run_cpu_benchmark` returns a dict.

**Wasted work**: Document construction, loop structure, and timing measurement are all repeated verbatim.

**Fix**: Refactor `test_cpu_linting_large_yaml()` to call `_run_cpu_benchmark()` and assert on its returned `total_ms`:

```python
def test_cpu_linting_large_yaml() -> None:
    timing = _run_cpu_benchmark()
    elapsed_s = timing["total_ms"] / 1000.0
    mean_ms = timing["mean_ms"]
    print(f"\nCPU BENCHMARK: {_ITERATIONS} iterations in {elapsed_s:.3f}s (mean {mean_ms:.3f} ms/iter)")
    assert elapsed_s < _TIME_LIMIT_SECONDS, (
        f"CPU benchmark exceeded {_TIME_LIMIT_SECONDS}s limit: {elapsed_s:.3f}s"
    )
```

Also note: line 112 raises `AssertionError` (misspelled -- missing 'r': should be `AssertionError` is not a real builtin, this is actually a custom exception name that shadows nothing, but the intent was clearly `AssertionError`).

---

### 2. mmap context manager scoping allows temp_path leak (frontmatter.py:34-71)

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`
**Lines**: 34-71

The `temp_path` variable is created at line 57 (`temp_path = file_path + ".tmp"`) and written to inside the `with` block for the mmap (lines 34-68). The `Path.replace()` call at line 71 is **outside** the `with` block. If an exception occurs during `temp_file.write()` (lines 60-68), the orphan `.tmp` file is never cleaned up.

Additionally, the mmap is held open during the entire temp-file write operation (lines 58-68). The mmap is only needed to read `mm[frontmatter_end_index:]` at line 68, but the context manager scope forces it to remain mapped for the duration of all preceding writes.

**Fix**:
- Read the body bytes from mmap into a variable, then exit the mmap context before writing the temp file.
- Wrap the temp-file creation and replace in a try/finally to guarantee cleanup:

```python
with pathlib.Path(file_path).open("r+b") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
    if mm[:len(DELIMITER)] != DELIMITER:
        return
    end_pos = mm.find(DELIMITER, len(DELIMITER))
    if end_pos == -1:
        return
    frontmatter_end_index = end_pos + len(DELIMITER)
    raw_yaml = mm[len(DELIMITER):end_pos]
    needs_fix, new_yaml_bytes = lint_and_fix(raw_yaml)
    if not needs_fix or new_yaml_bytes is None:
        return
    body_tail = mm[frontmatter_end_index:]  # read while mmap is open

# mmap now closed; write temp file with cleanup guarantee
temp_path = file_path + ".tmp"
try:
    with pathlib.Path(temp_path).open("wb") as temp_file:
        temp_file.write(DELIMITER)
        temp_file.write(new_yaml_bytes)
        if not new_yaml_bytes.endswith(b"\n"):
            temp_file.write(b"\n")
        temp_file.write(DELIMITER)
        temp_file.write(body_tail)
    pathlib.Path(temp_path).replace(file_path)
except BaseException:
    pathlib.Path(temp_path).unlink(missing_ok=True)
    raise
```

---

### 3. TOCTOU race in frontmatter.py empty-file check (frontmatter.py:31-34)

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`
**Lines**: 31-34

`pathlib.Path(file_path).stat().st_size` is called at line 31, then the file is opened at line 34. Between these two calls the file could be modified or deleted (classic TOCTOU). Additionally, `pathlib.Path(file_path)` is constructed three separate times (lines 31, 34, 58) instead of once.

**Fix**: Remove the separate stat check. Open the file unconditionally and check `mm.size() == 0` or handle the empty-file case after opening. Construct the Path once:

```python
p = pathlib.Path(file_path)
with p.open("r+b") as f:
    if f.seek(0, 2) == 0:  # seek to end, check size
        return
    f.seek(0)
    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        ...
```

---

## MEDIUM Priority

### 4. Sequential subprocess calls in bench_io._run_once() (bench_io.py:53-55)

**File**: `/home/user/agentskills-linter/scripts/bench_io.py`
**Lines**: 53-55

`shutil.which("skilllint")` is called on every invocation of `_run_once()`. In `run_benchmark()` (line 78-80) this means the PATH lookup is repeated `runs` times (default 3). The executable location will not change between iterations.

**Fix**: Resolve the executable once in `run_benchmark()` and pass the path to `_run_once()`:

```python
def run_benchmark(plugin_dir: Path, runs: int = 3) -> dict[str, float | int]:
    skilllint_exe = shutil.which("skilllint")
    if skilllint_exe is None:
        raise FileNotFoundError("'skilllint' executable not found on PATH")
    timings = [_run_once(plugin_dir, skilllint_exe) * 1000.0 for _ in range(runs)]
    ...
```

---

### 5. plugin_file_count fixture is function-scoped but data is session-scoped (conftest.py:51-61)

**File**: `/home/user/agentskills-linter/tests/benchmarks/conftest.py`
**Lines**: 51-61

`plugin_file_count` is decorated with `@pytest.fixture` (function scope) but depends on `extracted_plugin_dir` which is session-scoped. The `rglob("SKILL.md")` traversal at line 61 re-walks the entire directory tree for every test function that requests this fixture. The file count cannot change because the extraction is session-scoped.

**Fix**: Change to `@pytest.fixture(scope="session")` to compute once per session.

---

### 6. _write_result reads-then-writes without file locking (test_benchmark.py:49-61)

**File**: `/home/user/agentskills-linter/tests/benchmarks/test_benchmark.py`
**Lines**: 49-61

`_write_result` reads the entire JSON file, appends to the list, and writes it back. Under concurrent test execution (e.g., `pytest-xdist`) this is a race condition that can lose data. Even without concurrency, the read-modify-write pattern loads the entire history into memory each time.

**Fix**: For append-only writes, use JSONL (one JSON object per line) with `open("a")`, which is atomic at the OS level for small writes and avoids reading the file at all.

---

### 7. _get_git_info spawns two separate subprocesses (test_benchmark.py:15-36)

**File**: `/home/user/agentskills-linter/tests/benchmarks/test_benchmark.py`
**Lines**: 15-36

Two subprocess calls are made to get SHA and branch. These could be combined into a single `git log -1 --format=%h%n%D` call, halving the process spawn overhead.

**Fix**:
```python
def _get_git_info() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%h%n%(decorate:prefix=,suffix=,separator= ,tag=,pointer=)"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip().split("\n", 1)
        sha = out[0]
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"
    return sha, branch
```

Alternatively, keep both calls but run them with a single `git` invocation using multiple format placeholders is not straightforward for `rev-parse`, so at minimum cache the result since git info does not change within a test session.

---

## LOW Priority

### 8. Redundant double-rounding in build_gh_benchmark_array (bench_io.py:103-113)

**File**: `/home/user/agentskills-linter/scripts/bench_io.py`
**Lines**: 103-113

Values are already `round()`ed in `run_benchmark()` (lines 85-87), then `round()`ed again in `build_gh_benchmark_array()` (lines 110-113). The second round is a no-op.

---

### 9. generate_violations_fixture: SKILL_BODY.format() called per skill (generate_violations_fixture.py:237)

**File**: `/home/user/agentskills-linter/scripts/generate_violations_fixture.py`
**Line**: 237

`SKILL_BODY.format(title=..., violation=...)` is called once per skill (200 times by default). Since there are only 5 violation types and the title follows a pattern, the body could be cached per violation type using `functools.lru_cache` or a pre-built dict. Impact is minimal at 200 iterations but relevant if count is increased.

---

### 10. pathlib.Path constructed repeatedly from same string (frontmatter.py:31,34,58,71)

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`

`pathlib.Path(file_path)` is constructed 4 times from the same string argument. Each construction involves parsing, normalization, and object allocation. Store once in a local variable.
