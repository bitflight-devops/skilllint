# Code Smell Report: frontmatter.py

**File**: `/home/user/agentskills-linter/packages/skilllint/frontmatter.py`
**Date**: 2026-03-13T05:45:22Z

## Issues Found

### HIGH: temp_path leaked on exception (lines 57-71)

If an exception occurs during `temp_file.write(...)` (lines 60-68), the temp file at
`file_path + ".tmp"` is created but never cleaned up. The `pathlib.Path(temp_path).replace()`
on line 71 sits outside the `with` block that writes the temp file, so any write error
leaves an orphan `.tmp` file on disk.

- **Lines**: 57-71
- **Impact**: Leaked temp files accumulate across large batch runs.
- **Fix**: Wrap lines 57-71 in a try/finally that calls
  `pathlib.Path(temp_path).unlink(missing_ok=True)` on failure, or move the
  `.replace()` inside the `with` block after flushing.

### HIGH: mmap used after context manager exit (line 68)

The mmap `mm` and file handle `f` are opened in the `with` statement on line 34.
The temp file write on line 68 (`temp_file.write(mm[frontmatter_end_index:])`) reads
from the mmap inside a nested `with` block that is still within the outer `with`
scope, so this is actually fine. However, the `.replace()` on line 71 occurs
**outside** the outer `with` block. This is correct because the mmap is no longer
needed at that point. The scoping is actually valid.

UPDATE: mmap scoping is correct. Downgrading to informational.

### MEDIUM: Redundant Path construction (lines 31, 34)

`pathlib.Path(file_path)` is constructed twice: once for `.stat()` on line 31 and
again for `.open()` on line 34. Minor but wasteful.

- **Lines**: 31, 34
- **Fix**: Store `p = pathlib.Path(file_path)` once and reuse.

### MEDIUM: TOCTOU race on empty-file check (line 31)

`pathlib.Path(file_path).stat().st_size == 0` checks size, then separately opens the
file on line 34. The file could change between these two operations.

- **Lines**: 31, 34
- **Impact**: Low in practice but violates defensive programming principles.
- **Fix**: Remove the stat check; let mmap handle 0-length files (it raises
  ValueError for length 0, which can be caught).
