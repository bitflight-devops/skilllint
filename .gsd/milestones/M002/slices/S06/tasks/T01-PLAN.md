---
estimated_steps: 5
estimated_files: 2
---

# T01: Run external repo scans, capture output, and write findings report

**Slice:** S06 — External scan proof and findings report
**Milestone:** M002

## Description

Execute real `uv run python -m skilllint.plugin_validator check` against the three official external repos (`../claude-plugins-official`, `../skills`, `../claude-code-plugins`). Capture full output and exit codes. Write a structured findings report and a verification script.

## Steps

1. Run `uv run python -m skilllint.plugin_validator check ~/repos/claude-plugins-official` and capture stdout + exit code
2. Run `uv run python -m skilllint.plugin_validator check ~/repos/skills` and capture stdout + exit code
3. Run `uv run python -m skilllint.plugin_validator check ~/repos/claude-code-plugins` and capture stdout + exit code
4. Write `scripts/verify-s06.sh` — a bash script that runs all three scans and asserts exit codes: claude-plugins-official=1 (genuine FM003/FM005 errors), skills=1, claude-code-plugins=0 (warnings only). Script should exit 0 on success, 1 on any mismatch.
5. Write `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — structured report with: per-repo table of error count + warning count, list of remaining hard failures (FM003/FM005) with file paths, summary of warning-level findings, and a human review recommendation section.

## Must-Haves

- [ ] All three external repos scanned via real CLI path
- [ ] Exit codes match S04 baseline: claude-plugins-official=1, skills=1, claude-code-plugins=0
- [ ] `scripts/verify-s06.sh` automates exit code verification and exits 0
- [ ] Findings report documents every remaining hard failure with rule code and file path

## Verification

- `bash scripts/verify-s06.sh` exits 0
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` exists and contains per-repo breakdown

## Inputs

- S04 established exit code baseline: claude-plugins-official=1, skills=1, claude-code-plugins=0
- S04 severity classification: FM003/FM005 = error, FM004/FM007/AS004 = warning
- External repos at `~/repos/claude-plugins-official`, `~/repos/skills`, `~/repos/claude-code-plugins`
- CLI entry point: `uv run python -m skilllint.plugin_validator check <path>`

## Expected Output

- `scripts/verify-s06.sh` — executable verification script
- `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` — structured findings report for human review

## Observability Impact

- **Signals changed:** Three new scan outputs captured; exit codes and stdout logged for each repo
- **Future inspection:** Run `bash scripts/verify-s06.sh` to re-verify exit codes; read `.gsd/milestones/M002/slices/S06/S06-FINDINGS-REPORT.md` for detailed findings
- **Failure visibility:** Script prints mismatch details; report lists every hard failure with rule code and file path
