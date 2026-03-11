# Vendor Doc Change Detection and Schema Drift Notification

**Date**: 2026-03-11
**Status**: Planning
**Components**: 3 (fetch script extension, SessionStart hook, drift auditor agent)

---

## Overview

Detect when upstream vendor documentation changes and surface evidence-based drift reports so schema fields can be audited against their declared sources.

Three components work together:

1. **`scripts/fetch_platform_docs.py`** -- extended with snapshot/compare logic and a `.drift-pending.json` output
2. **`.claude/hooks/vendor-drift-check.js`** -- SessionStart hook that runs the fetch script and injects context when changes are detected
3. **`.claude/agents/schema-drift-auditor.md`** -- agent that reads drift data, cross-references schema `x-audited.source` fields, and writes an evidence report

---

## Existing Codebase Facts

These facts were verified from file reads on 2026-03-11:

| Item | Verified Value |
|------|---------------|
| Fetch script path | `scripts/fetch_platform_docs.py` |
| Fetch script dependencies | `typer>=0.21.0`, `rich>=13.0`, `httpx>=0.27.0` |
| Fetch script PEP 723 shebang | `#!/usr/bin/env -S uv --quiet run --active --script` |
| Git platform class | `GitPlatform` with `name`, `url` slots |
| HTTP platform class | `DocSitePlatform` with `name`, `pages` slots; `DocPage` with `url`, `filename` slots |
| Git update function | `clone_or_update_repo(platform, *, dry_run)` |
| HTTP fetch function | `fetch_doc_site(platform, *, dry_run)` |
| Vendor directory | `.claude/vendor/` (computed as `PROJECT_ROOT / ".claude" / "vendor"`) |
| Hook file extension | `.js` (CommonJS, executed with `node`) |
| Hook stdin/stdout | JSON protocol: stdin receives hook context, stdout emits `hookSpecificOutput.additionalContext` |
| Settings file | `.claude/settings.json` with `hooks.SessionStart` array |
| Existing SessionStart hook | `node .claude/hooks/gsd-check-update.js` |
| Agent frontmatter fields | `name`, `description`, `tools`, `color`, `skills` |
| Schema field audit marker | `x-audited: { date, source }` on each field in `packages/skilllint/schemas/<provider>/v1.json` |
| Schema source values | Paths like `.claude/vendor/cursor/rules.md`, `.claude/vendor/claude_code/plugins/...` |
| `.claude/vendor/*` gitignore | Already exists (vendor dir is gitignored) |

---

## Component 1: Fetch Script Change Detection

### File: `scripts/fetch_platform_docs.py`

Extend the existing fetch script to snapshot state before updates, compare after, and write drift data.

### Exit Code Contract

| Exit Code | Meaning |
|-----------|---------|
| 0 | No changes detected (or first run with no prior state) |
| 2 | Changes detected; `.drift-pending.json` written |

Dry-run mode always exits 0 regardless of detected changes.

### `.drift-pending.json` Output Path

`.claude/vendor/.drift-pending.json` -- gitignored by existing `.claude/vendor/*` pattern.

### `.drift-pending.json` Schema

```json
{
  "fetch_time": "2026-03-11T09:00:00Z",
  "changed": [
    {
      "provider": "cursor",
      "type": "http",
      "files": [
        {
          "filename": "rules.md",
          "before_hash": "abc123...",
          "after_hash": "def456...",
          "before_content": "... full text before ...",
          "after_content": "... full text after ..."
        }
      ],
      "changelog": "... fetched releases page content or null ..."
    },
    {
      "provider": "claude_code",
      "type": "git",
      "before_sha": "a1b2c3d",
      "after_sha": "d4e5f6a",
      "diff": "... git diff output of relevant doc files ...",
      "changelog": "... git log --oneline a1b2c3d..d4e5f6a ..."
    }
  ]
}
```

### Implementation Tasks

#### Task 1.1: Add snapshot infrastructure and data model

- [ ] Add `import hashlib`, `import json`, `from datetime import datetime, UTC` to imports
- [ ] Add `DRIFT_FILE = VENDOR_DIR / ".drift-pending.json"` constant
- [ ] Define `@dataclass` classes for drift results: `GitDriftResult`, `HttpFileDriftResult`, `HttpDriftResult`, `DriftReport`
- [ ] Add helper `_sha256(text: str) -> str` that returns hex digest of content
- [ ] Add helper `_read_text_or_none(path: Path) -> str | None` for safe file reads
- [ ] Tests: unit tests for `_sha256`, `_read_text_or_none`, dataclass serialization

#### Task 1.2: Add git snapshot/compare logic

- [ ] Create function `_git_head_sha(repo_dir: Path) -> str | None` -- runs `git rev-parse HEAD` and returns SHA or None if not a repo
- [ ] Modify `clone_or_update_repo` to accept and return snapshot data:
  - Before pull/clone: capture `before_sha = _git_head_sha(dest)`
  - After pull/clone: capture `after_sha = _git_head_sha(dest)`
  - If `before_sha != after_sha` and both are not None:
    - Capture `git diff <before_sha>..<after_sha> -- <doc file patterns>` (limit to doc-relevant paths: `*.md`, `docs/`, `CLAUDE.md`, etc.)
    - Capture `git log --oneline <before_sha>..<after_sha>`
  - Return `GitDriftResult | None`
- [ ] Tests: mock `_run_git` to test snapshot capture, diff extraction, no-change path, first-clone path (before_sha is None)

#### Task 1.3: Add HTTP snapshot/compare logic

- [ ] Modify `fetch_doc_site` to accept and return snapshot data:
  - Before fetch: read existing file content and compute SHA-256 hash
  - After fetch: compute SHA-256 hash of new content
  - If hashes differ: store before/after content and hashes in `HttpFileDriftResult`
  - Return `HttpDriftResult | None` (None if no files changed)
- [ ] Research and add a `releases_url` field to each `DocSitePlatform` definition:
  - `cursor`: research the Cursor changelog/releases page URL
  - `copilot_cli`: research the GitHub Copilot CLI changelog URL
  - When changes are detected, fetch the releases URL content and include as `changelog`
- [ ] Tests: mock httpx client to test hash comparison, changed/unchanged paths, releases URL fetch

#### Task 1.4: Write drift report and exit code logic

- [ ] Create function `_write_drift_report(report: DriftReport) -> None` -- serializes to JSON and writes to `DRIFT_FILE`
- [ ] Modify the `fetch` command:
  - Collect all `GitDriftResult` and `HttpDriftResult` results from Phase A and Phase B
  - Filter to only those that detected changes
  - If any changes detected and not dry-run:
    - Build `DriftReport` with `fetch_time=datetime.now(UTC).isoformat()` and changed providers
    - Call `_write_drift_report`
    - Print summary panel showing which providers changed
    - `raise typer.Exit(code=2)`
  - If no changes or dry-run: exit normally (code 0)
- [ ] Tests: end-to-end test of the `fetch` command with mocked git/httpx that verifies:
  - Exit code 2 when changes detected
  - Exit code 0 when no changes
  - `.drift-pending.json` content matches expected schema
  - Dry-run always exits 0

#### Task 1.5: Quality gate

- [ ] `uv run ruff format scripts/fetch_platform_docs.py`
- [ ] `uv run ruff check scripts/fetch_platform_docs.py`
- [ ] Type checker passes on the script
- [ ] All new and existing tests pass: `uv run pytest tests/ -k fetch_platform`
- [ ] Coverage >= 80% on touched code
- [ ] `/python3-development:shebangpython scripts/fetch_platform_docs.py` -- verify PEP 723 metadata includes any new dependencies (e.g., if none added, confirm existing deps suffice)

---

## Component 2: SessionStart Hook

### File: `.claude/hooks/vendor-drift-check.js`

A Node.js CommonJS script that runs the fetch script and injects context into the session when vendor changes are detected.

### Implementation Tasks

#### Task 2.1: Create the hook script

- [ ] Create `.claude/hooks/vendor-drift-check.js`
- [ ] Follow existing hook patterns from `.claude/hooks/gsd-check-update.js`:
  - Shebang: `#!/usr/bin/env node`
  - CommonJS: `const { spawn } = require('child_process');` etc.
  - Read stdin JSON (hook context)
  - Execute `uv run scripts/fetch_platform_docs.py` as a child process
  - Capture exit code
- [ ] Exit code handling:
  - Exit code 0: output empty JSON `{}` (silent -- no context injection)
  - Exit code 2: output JSON with `additionalContext` message:
    ```json
    {
      "hookSpecificOutput": {
        "additionalContext": "Vendor documentation has changed. `.claude/vendor/.drift-pending.json` lists affected providers with diffs and changelogs. Run the schema-drift-auditor agent to assess whether schema fields are affected."
      }
    }
    ```
  - Other exit codes: log error to stderr, output empty JSON (do not block session start)
- [ ] Set a reasonable timeout (60 seconds) for the fetch script -- network operations may be slow
- [ ] Handle the case where `uv` is not found (log warning, exit silently)

#### Task 2.2: Register the hook in settings.json

- [ ] Edit `.claude/settings.json`
- [ ] Add a new entry to the `hooks.SessionStart` array:
  ```json
  {
    "hooks": [
      {
        "type": "command",
        "command": "node .claude/hooks/vendor-drift-check.js"
      }
    ]
  }
  ```
- [ ] Preserve all existing hooks and settings

#### Task 2.3: Manual verification

- [ ] Run `node .claude/hooks/vendor-drift-check.js < /dev/null` and verify it executes without crashing
- [ ] Verify JSON output format is correct when piped to `jq`
- [ ] Test with a simulated exit code 2 scenario (manually create a `.drift-pending.json` and verify the context message)

---

## Component 3: Schema Drift Auditor Agent

### File: `.claude/agents/schema-drift-auditor.md`

A Claude Code agent that reads drift data, cross-references schema fields, and produces an evidence report.

### Implementation Tasks

#### Task 3.1: Create the agent file

- [ ] Create `.claude/agents/schema-drift-auditor.md` with frontmatter:
  ```yaml
  ---
  name: schema-drift-auditor
  description: Reads .drift-pending.json, cross-references vendor doc changes against schema x-audited.source fields, and writes an evidence-based drift report. Detection only -- does not modify schemas.
  tools: Read, Glob, Grep, Write
  color: yellow
  ---
  ```
- [ ] Agent body must include these sections:

**Role and Purpose**:
- You are a schema drift auditor. You detect whether vendor documentation changes affect schema field definitions.
- You produce evidence-based reports. You do NOT modify any schema files.

**Input**:
- Read `.claude/vendor/.drift-pending.json`
- If the file does not exist or is empty, report "No drift pending" and exit

**For Each Changed Provider** (from `changed` array):
1. Identify the provider name (e.g., `cursor`, `claude_code`)
2. Find the corresponding schema file: `packages/skilllint/schemas/<provider>/v1.json`
3. If no schema file exists for this provider, note it and skip
4. Read the schema file and extract all fields that have `x-audited.source` pointing to files within `.claude/vendor/<provider>/`
5. Read the diff/changelog data from the drift entry:
   - For `type: "git"`: read the `diff` and `changelog` fields
   - For `type: "http"`: read the `before_content` and `after_content` for each changed file, plus `changelog`
6. For each affected schema field, assess whether the diff impacts it:
   - Renamed concepts (term used in field description appears renamed in diff)
   - New fields in vendor docs not present in schema
   - Removed fields from vendor docs that exist in schema
   - Changed required/optional status
   - Deprecated terms or features
   - Structural changes (nesting, type changes)
7. Classify each finding as:
   - **STALE**: Field is likely outdated based on vendor change evidence
   - **NEW**: Vendor docs describe something not in schema
   - **REMOVED**: Vendor docs no longer mention something in schema
   - **REVIEW**: Change is ambiguous -- human judgment needed
8. Quote specific evidence from the diff/changelog for each finding

**Output**:
- Write findings to `.claude/vendor/.drift-report.md` (gitignored, overwritten each run)
- Report format:

```markdown
# Schema Drift Report

**Generated**: <timestamp>
**Providers with changes**: <list>

## Provider: <name>

**Schema file**: `packages/skilllint/schemas/<provider>/v1.json`
**Vendor change type**: git | http
**Changelog summary**: <one-line summary>

### Findings

| Field Path | Status | Evidence | Source File |
|------------|--------|----------|-------------|
| `properties.rules.items.type` | STALE | Vendor renamed "rules" to "instructions" in diff line 42 | `.claude/vendor/cursor/rules.md` |
| (new) `properties.context` | NEW | Vendor docs now describe a `context` block not present in schema | `.claude/vendor/cursor/rules.md` |

### Raw Diff Reference

<details>
<summary>Click to expand diff</summary>

\`\`\`diff
... diff content ...
\`\`\`

</details>
```

**Constraints**:
- Do NOT modify schema files
- Do NOT apply changes
- Do NOT delete `.drift-pending.json` (leave it for human review)
- If no findings for a provider, state "No schema impact detected" with reasoning

#### Task 3.2: Verify agent frontmatter

- [ ] Confirm frontmatter fields match the format used by existing agents in `.claude/agents/`
- [ ] Confirm `tools` list includes only what the agent needs (Read, Glob, Grep, Write)
- [ ] Confirm agent does NOT have Edit tool (it must not modify schema files)

---

## Dependency Graph

```text
Task 1.1  (data model + helpers)
  |
  +---> Task 1.2  (git snapshot/compare)
  |       |
  +---> Task 1.3  (HTTP snapshot/compare)
  |       |
  +-------+---> Task 1.4  (drift report + exit code)
                  |
                  +---> Task 1.5  (quality gate)
                          |
                          +---> Task 2.1  (hook script)
                                  |
                                  +---> Task 2.2  (register hook)
                                  |
                                  +---> Task 2.3  (manual verify)

Task 3.1  (agent file)  -- independent, can run in parallel with any task
  |
  +---> Task 3.2  (verify frontmatter)
```

---

## Commit Plan

Each commit corresponds to a completed task or tightly coupled task pair:

| Commit | Tasks | Description |
|--------|-------|-------------|
| 1 | 1.1 | feat: add drift detection data model and hash helpers to fetch script |
| 2 | 1.2 | feat: add git snapshot/compare logic with diff capture |
| 3 | 1.3 | feat: add HTTP snapshot/compare logic with content hashing |
| 4 | 1.4 | feat: write drift-pending.json and exit code 2 on vendor changes |
| 5 | 1.5 | chore: quality gate pass for fetch script drift detection |
| 6 | 2.1 + 2.2 | feat: add vendor-drift-check SessionStart hook |
| 7 | 2.3 | test: verify hook execution and JSON output |
| 8 | 3.1 + 3.2 | feat: add schema-drift-auditor agent |

---

## Testing Strategy

### Unit Tests (Task 1.1 -- 1.3)

Location: `tests/test_fetch_platform_docs.py` (or `tests/scripts/test_fetch_platform_docs.py` depending on existing test layout)

- `test_sha256_returns_hex_digest`
- `test_sha256_same_input_same_output`
- `test_read_text_or_none_existing_file_returns_content`
- `test_read_text_or_none_missing_file_returns_none`
- `test_git_head_sha_returns_sha_for_valid_repo`
- `test_git_head_sha_returns_none_for_non_repo`
- `test_clone_or_update_repo_detects_change_returns_drift_result`
- `test_clone_or_update_repo_no_change_returns_none`
- `test_clone_or_update_repo_first_clone_returns_none`
- `test_fetch_doc_site_detects_content_change_returns_drift_result`
- `test_fetch_doc_site_no_change_returns_none`
- `test_fetch_doc_site_first_fetch_returns_none`

### Integration Tests (Task 1.4)

- `test_fetch_command_exits_2_when_changes_detected`
- `test_fetch_command_exits_0_when_no_changes`
- `test_fetch_command_writes_drift_pending_json`
- `test_fetch_command_dry_run_exits_0_regardless`
- `test_drift_pending_json_matches_schema`

### Hook Tests (Task 2.3)

Manual verification (not pytest) -- the hook is a Node.js script:
- Run with empty stdin, verify no crash
- Run with simulated exit code 2 from fetch script, verify JSON output contains `additionalContext`
- Verify valid JSON output with `jq`

---

## Research Items

These items require investigation at implementation time:

- [ ] **Cursor changelog URL**: Find the public URL for Cursor's changelog or release notes page. Candidate: `https://cursor.com/changelog` or similar. Verify it returns parseable content via httpx.
- [ ] **Copilot CLI changelog URL**: Find the GitHub Copilot CLI changelog. Candidate: GitHub releases page for the copilot CLI repo, or the docs changelog page. Verify accessibility.
- [ ] **Existing test layout**: Check whether `tests/` has subdirectories for scripts or if tests are flat. Match existing convention.
- [ ] **Git doc file patterns**: For each `GitPlatform`, determine which file paths within the cloned repo are relevant for schema auditing (e.g., `CLAUDE.md`, `docs/**/*.md`, `src/**/schema*`). These patterns are used to scope the `git diff` output.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Fetch script takes too long for SessionStart hook | 60-second timeout in hook; fetch script already uses shallow clones (`--depth 1`) |
| Network unavailable at session start | Hook catches non-zero exit codes (other than 2) silently; does not block session |
| `.drift-pending.json` grows very large with full content | HTTP platforms have few pages (1-2 each); git diffs are scoped to doc-relevant paths only |
| First run has no prior state to compare | Return None / skip drift detection on first clone or first HTTP fetch (no before_sha / no existing file) |
| Agent hallucinates schema impact | Agent is instructed to quote specific evidence from diffs; REVIEW status for ambiguous cases |
| Schema file does not exist for a changed provider | Agent skips provider and notes the gap in the report |
