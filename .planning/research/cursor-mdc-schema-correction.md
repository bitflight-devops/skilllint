---
research-type: schema-correction
subject: Cursor .mdc rule file frontmatter schema
date: 2026-03-10
status: COMPLETE
sources:
  - url: https://cursor.com/docs/context/rules (via sanjeed5/awesome-cursor-rules-mdc)
    confidence: HIGH — official Cursor docs content confirmed
  - file: .planning/phases/02-platform-adapters/02-RESEARCH.md
  - file: packages/skilllint/schemas/cursor/v1.json
  - file: packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc
  - file: .planning/phases/02-platform-adapters/02-03-PLAN.md
  - file: .planning/phases/02-platform-adapters/02-03-SUMMARY.md
---

# Cursor .mdc Schema Correction Research

## Summary

The current schema at `packages/skilllint/schemas/cursor/v1.json` marks `description` as a
required field. The official Cursor docs establish that `description` is only required when the
rule type is "Apply Intelligently". It is NOT universally required. Additionally, the `type` field
appears in the `invalid_rule.mdc` fixture but is not a documented frontmatter field.

---

## What the Official Docs Actually Say

Source: Cursor rules documentation (fetched from the docs reference repo). Direct quotes:

### Valid frontmatter fields

The docs show this minimal frontmatter in the `RULE.md file format` section:

```markdown
---
description: "This rule provides standards for frontend components and API validation"
alwaysApply: false
---
```

And in the `Rule anatomy` section, the example shows:

```markdown
---
globs:
alwaysApply: false
---
```

No `description` field present in that example at all.

The three fields controlled by the "type dropdown" in the UI are: `description`, `globs`,
`alwaysApply`. These are the only three officially documented frontmatter fields.

### Conditional requirement for `description`

From the FAQ section of the official docs (verbatim):

> "For `Apply Intelligently`, ensure a description is defined."

This directly establishes that `description` is only required for the "Apply Intelligently" rule
type. The other three rule types (`Always Apply`, `Apply to Specific Files`, `Apply Manually`) do
not require `description`.

### The four rule types and their frontmatter implications

| Rule Type              | description | globs       | alwaysApply |
|------------------------|-------------|-------------|-------------|
| Always Apply           | optional    | optional    | true        |
| Apply Intelligently    | REQUIRED    | optional    | false       |
| Apply to Specific Files| optional    | REQUIRED    | false       |
| Apply Manually         | optional    | not used    | false       |

None of these combinations require `description` universally.

### The `type` field

The `type` field does NOT appear anywhere in the official Cursor docs as a frontmatter field. It
appears in some community-written examples and tutorials but is not part of the documented schema.
Its status is: unknown/unofficial.

### Legacy `.mdc` files

As of Cursor 2.2, standalone `.mdc` files are legacy. New rules are created as folders with a
`RULE.md` file inside. However, `.mdc` files "will remain functional". The frontmatter schema for
`.mdc` files uses the same three fields: `description`, `globs`, `alwaysApply`.

---

## Correct Schema for `file_types.mdc`

### Required fields

**None.** No field is universally required. An empty frontmatter (or no frontmatter) is valid for
"Always Apply" rules that work without description or globs.

### Optional fields

- `description` — string, minLength 1. Required only when rule type is "Apply Intelligently", but
  the schema cannot enforce this conditional requirement without knowing which rule type is intended.
  Keep as optional with no minimum length enforcement at the schema level, or keep minLength: 1 if
  present (i.e., if the field is provided, it must be non-empty).
- `globs` — string or array of strings. Optional. Controls auto-attach behavior.
- `alwaysApply` — boolean. Optional. When true, rule injects into every context.

### `additionalProperties` setting

`additionalProperties: false` is a judgment call. Arguments:

- **For `false`**: The three documented fields are the only ones the Cursor UI exposes. Rejecting
  unknown fields helps catch typos (e.g., `glob` instead of `globs`).
- **Against `false`**: Community examples show additional fields (`title`, `tags`, `priority`,
  `version`) that some users add. These are not official but are not harmful. The Cursor parser
  appears to silently ignore unknown frontmatter keys.

**Recommendation**: Keep `additionalProperties: false` to enforce the documented schema. The linter
exists to validate against the official spec, not community extensions. Unknown fields should be
flagged as warnings so users know they are using undocumented fields.

### Correct `required` array

```json
"required": []
```

Or equivalently, omit the `required` key entirely.

### Corrected schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Cursor MDC Rule Frontmatter",
  "type": "object",
  "required": [],
  "properties": {
    "description": { "type": "string", "minLength": 1 },
    "globs": {
      "oneOf": [
        { "type": "string" },
        { "type": "array", "items": { "type": "string" } }
      ]
    },
    "alwaysApply": { "type": "boolean" }
  },
  "additionalProperties": false
}
```

Note: `"required": []` is equivalent to omitting `required`. Either form is valid JSON Schema
draft-07. Omitting it is slightly cleaner.

---

## What Makes an `.mdc` File Actually Invalid

Given the corrected schema, an `.mdc` file is invalid when:

1. **A documented field has the wrong type** — e.g., `alwaysApply: "yes"` (string instead of
   boolean), or `description: 42` (integer instead of string).
2. **`description` is present but empty** — `description: ""` violates `minLength: 1`.
3. **An unknown frontmatter field is present** — any field other than `description`, `globs`,
   `alwaysApply` violates `additionalProperties: false`.
4. **`globs` has an invalid type** — e.g., `globs: 42` (integer instead of string or array).

What does NOT make an `.mdc` file invalid:
- Missing `description` — valid. Cursor supports rules without description ("Always Apply" type).
- Missing `globs` — valid. Not all rule types use globs.
- Missing `alwaysApply` — valid. Defaults to false behavior when absent.
- Empty frontmatter block (`---\n---`) — valid. Rule with no metadata is a manual-only rule.

---

## Current `invalid_rule.mdc` Fixture Analysis

File: `packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc`

```yaml
---
type: rule
---
```

Current fixture comment: "This .mdc file is missing the required 'description' field."

**Problem with current fixture**: The stated reason for invalidity is wrong. Under the corrected
schema, `description` is not required. The file IS invalid, but for the correct reason: `type` is
not a documented frontmatter field, so it violates `additionalProperties: false`.

**Recommended fixture correction**: Update the comment to reflect the actual reason:

```markdown
---
type: rule
---

# Invalid Rule

This .mdc file contains an unknown frontmatter field ("type") which is not part of
the documented Cursor .mdc schema (description, globs, alwaysApply).
```

The fixture itself (the `type: rule` field) is already the correct content to trigger an
`additionalProperties` violation. Only the explanatory comment needs updating.

---

## Existing Files with Incorrect Claims

### 1. `packages/skilllint/schemas/cursor/v1.json` (lines 13-19)

**Incorrect claim**: `"required": ["description"]`

**Correct form**: Remove `description` from `required` (or use `"required": []`).

```json
// BEFORE (incorrect)
"required": ["description"],

// AFTER (correct)
```
(omit `required` entirely, or use `"required": []`)

### 2. `.planning/phases/02-platform-adapters/02-03-PLAN.md` (lines 88-97)

**Incorrect claim** in Task 1 `<action>` section:
```json
"required": ["description"],
```
This is the source schema specification that was implemented. It incorrectly specifies `description`
as required.

**Location**: Line 91 in the JSON block inside Task 1.

**Correction**: Change `"required": ["description"]` to omit `required` or use `"required": []`.

Note: This is a historical plan file. The plan has already been executed (per 02-03-SUMMARY.md:
"None - plan executed exactly as written"). The correction should be applied to `v1.json` (the
live artifact) and the PLAN.md updated for historical accuracy.

### 3. `.planning/phases/02-platform-adapters/02-03-SUMMARY.md` (line 63)

**Incorrect claim**:
> "file_types.mdc (description required, globs/alwaysApply optional, additionalProperties false)"

**Correct form**:
> "file_types.mdc (no required fields — description/globs/alwaysApply all optional,
> additionalProperties false)"

### 4. `.planning/phases/02-platform-adapters/02-RESEARCH.md` (lines 296-302)

**Claim to evaluate**:
> "`.mdc` frontmatter fields (Cursor rules):
> - `description` — required, brief explanation of the rule's purpose"

The word "required" here is technically incorrect per the official docs. The field is
**conditionally required** (only for "Apply Intelligently" rule type).

**Correction**: Change "required" to "optional; required only when rule type is 'Apply
Intelligently' (AI-decided activation)".

Similarly in lines 432-447 (Cursor .mdc Schema code block), the `"required": ["description"]`
JSON should be updated.

### 5. `packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc` (line 7)

**Incorrect claim** in comment: "This .mdc file is missing the required 'description' field."

**Correct form**: "This .mdc file contains an unknown frontmatter field ('type') which violates
additionalProperties: false. The 'description' field is not universally required."

---

## Recommended Corrections Per File

### Priority 1: Live artifact (must fix)

| File | Line(s) | Change |
|------|---------|--------|
| `packages/skilllint/schemas/cursor/v1.json` | 13 | Remove `"required": ["description"]` (or use `"required": []`) |
| `packages/skilllint/tests/fixtures/cursor/invalid_rule.mdc` | 7 | Update comment to state actual reason for invalidity |

### Priority 2: Planning docs (fix for accuracy)

| File | Line(s) | Change |
|------|---------|--------|
| `.planning/phases/02-platform-adapters/02-03-SUMMARY.md` | 63 | Change "description required" to "no required fields" |
| `.planning/phases/02-platform-adapters/02-RESEARCH.md` | 299, 436 | Change "required" to "optional (required only for Apply Intelligently type)" |
| `.planning/phases/02-platform-adapters/02-03-PLAN.md` | 91 | Update JSON block to remove description from required |

---

## Impact on Tests

The schema correction changes what the Cursor adapter validates. Tests asserting that a missing
`description` field produces a validation error will need updating. Specifically:

- Any test asserting that an `.mdc` file without `description` is invalid needs to be removed or
  updated. The fixture without `description` is valid under the corrected schema.
- Tests asserting that `type: rule` (or other unknown fields) produce a validation error remain
  correct — the `additionalProperties: false` constraint is unchanged.
- Tests asserting that `alwaysApply: "yes"` (wrong type) produce a validation error remain correct.

---

## Research Confidence

| Claim | Confidence | Source |
|-------|------------|--------|
| `description` is not universally required | HIGH | Official Cursor docs FAQ: "For Apply Intelligently, ensure a description is defined" |
| Valid fields are: description, globs, alwaysApply | HIGH | Official Cursor docs "type dropdown" section |
| `type` is not a documented field | HIGH | Absent from all official docs; present only in community examples |
| `additionalProperties: false` is appropriate | MEDIUM | Judgment call; official docs only document three fields; community use of extra fields is undocumented |
| Empty frontmatter is valid | HIGH | Rule anatomy example in official docs shows `globs:` and `alwaysApply: false` only, no description |
