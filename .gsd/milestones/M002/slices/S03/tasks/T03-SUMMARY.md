---
id: T03
parent: S03
milestone: M002
status: complete
completed_at: 2026-03-15T21:15:00-04:00
---

# T03: Add Discovery Contract Tests

**Status:** complete

## What Happened

Created `test_discovery_modes.py` with 16 tests covering:

### TestScanDiscoveryMode (2 tests)
- `test_discovery_mode_enum_values` - verifies enum values
- `test_provider_dir_names_includes_expected` - verifies provider dirs recognized

### TestReadPluginManifest (3 tests)
- `test_read_valid_manifest` - parses plugin.json with components
- `test_read_manifest_without_components` - handles minimal manifest
- `test_read_missing_manifest` - returns None when no plugin.json

### TestDetectDiscoveryMode (5 tests)
- `test_manifest_mode_with_explicit_components` - MANIFEST when explicit arrays
- `test_auto_mode_without_components` - AUTO when no explicit arrays
- `test_structure_mode_for_provider_dir` - STRUCTURE for .claude/
- `test_structure_mode_for_nested_provider_dir` - STRUCTURE for nested dirs
- `test_auto_mode_for_plain_directory` - AUTO for plain directories

### TestManifestDiscoveryPaths (1 test)
- `test_get_manifest_paths_existing_files` - extracts declared file paths

### TestStructureDiscoveryPaths (1 test)
- `test_get_structure_paths_claude_dir` - structure discovery for .claude/

### TestResolveFilterAndExpandPaths (4 tests)
- `test_expand_with_explicit_glob` - --filter glob expansion
- `test_expand_manifest_directory` - manifest-driven expansion
- `test_expand_provider_directory` - structure-based expansion
- `test_exclude_mutually_incompatible_filters` - mutual exclusion

## Verification

```
$ uv run pytest packages/skilllint/tests/test_discovery_modes.py -v --no-cov
16 passed in 1.80s
```