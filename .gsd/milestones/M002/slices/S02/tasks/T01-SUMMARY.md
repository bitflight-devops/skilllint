---
id: T01
parent: S02
milestone: M002
status: complete
completed_at: 2026-03-15T20:30:00-04:00
---

# T01: Map Validator Ownership

**Status:** complete

## What Happened

Added explicit ownership classification for all validators:

1. Created `ValidatorOwnership` enum with `SCHEMA` and `LINT` values
2. Created `VALIDATOR_OWNERSHIP` mapping dict classifying each validator
3. Created `get_validator_ownership()` function to look up ownership

**Schema-backed (hard failures):**
- FrontmatterValidator
- PluginStructureValidator
- PluginRegistrationValidator  
- HookValidator
- SymlinkTargetValidator

**Lint validators (warnings/findings):**
- NameFormatValidator
- DescriptionValidator
- ComplexityValidator
- InternalLinkValidator
- ProgressiveDisclosureValidator
- NamespaceReferenceValidator
- MarkdownTokenCounter

## Verification

- 8 ownership routing tests pass
- CLI still works: valid skill → exit 0, invalid skill → exit 1 with errors