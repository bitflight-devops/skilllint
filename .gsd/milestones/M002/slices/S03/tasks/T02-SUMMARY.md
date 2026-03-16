---
id: T02
parent: S03
milestone: M002
status: complete
completed_at: 2026-03-15T21:10:00-04:00
---

# T02: Implement Three-Mode Discovery

**Status:** complete

## What Happened

Updated `resolve_filter_and_expand_paths()` to use discovery modes:

1. Added `ScanDiscoveryMode` enum with MANIFEST, AUTO, STRUCTURE values
2. Added `get_manifest_discovery_paths()` to extract scan paths from explicit manifest
3. Added `get_structure_discovery_paths()` to extract scan paths for provider directories
4. Updated `resolve_filter_and_expand_paths()` to branch on discovery mode

**New logic in resolve_filter_and_expand_paths():**
```python
discovery_mode = detect_discovery_mode(path)

if discovery_mode == ScanDiscoveryMode.MANIFEST:
    manifest = read_plugin_manifest(path)
    if manifest:
        expanded_paths.extend(get_manifest_discovery_paths(manifest))
elif discovery_mode == ScanDiscoveryMode.AUTO:
    expanded_paths.extend(discover_validatable_paths(path))
elif discovery_mode == ScanDiscoveryMode.STRUCTURE:
    expanded_paths.extend(get_structure_discovery_paths(path))
```

## Verification

- 16 discovery mode tests pass
- Full test suite passes (83 passed, 1 skipped)
- CLI still works correctly