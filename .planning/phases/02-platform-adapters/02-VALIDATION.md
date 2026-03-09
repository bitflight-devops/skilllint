---
phase: 2
slug: platform-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config in `pyproject.toml`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_adapters.py tests/test_as_series.py -x -q` |
| **Full suite command** | `uv run pytest packages/skilllint/tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_adapters.py tests/test_as_series.py -x -q`
- **After every plan wave:** Run `uv run pytest packages/skilllint/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | ADPT-01 | unit | `uv run pytest tests/test_adapters.py::test_protocol_defined -x -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | ADPT-01 | unit | `uv run pytest tests/test_adapters.py::test_claude_code_adapter -x -q` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | ADPT-01 | unit | `uv run pytest tests/test_adapters.py::test_cursor_adapter -x -q` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | ADPT-01 | unit | `uv run pytest tests/test_adapters.py::test_codex_adapter -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | ADPT-02 | integration | `uv run pytest tests/test_adapters.py::test_entry_points_discovery -x -q` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 2 | ADPT-03 | integration | `uv run pytest tests/test_adapters.py::test_claude_code_validates_plugin_json -x -q` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 2 | ADPT-03 | integration | `uv run pytest tests/test_adapters.py::test_claude_code_validates_skill_md -x -q` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 2 | ADPT-03 | integration | `uv run pytest tests/test_adapters.py::test_claude_code_validates_hooks_json -x -q` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 2 | ADPT-04 | integration | `uv run pytest tests/test_adapters.py::test_cursor_validates_mdc -x -q` | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 2 | ADPT-05 | integration | `uv run pytest tests/test_adapters.py::test_codex_validates_agent_format -x -q` | ❌ W0 | ⬜ pending |
| 2-05-01 | 05 | 2 | ADPT-03 | unit | `uv run pytest tests/test_as_series.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_adapters.py` — stubs for ADPT-01 through ADPT-05 (Protocol, entry_points discovery, per-platform validation)
- [ ] `tests/test_as_series.py` — stubs for AS001–AS006 AgentSkills rule validation
- [ ] `tests/fixtures/claude_code/` — sample valid/invalid Claude Code plugin fixtures
- [ ] `tests/fixtures/cursor/` — sample valid/invalid `.mdc` rule files
- [ ] `tests/fixtures/codex/` — sample valid/invalid Codex agent format files

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Third-party adapter installed as separate package is discovered at runtime | ADPT-02 | Requires real package installation, not just mock | `pip install` a minimal test adapter package, run `skilllint --platform <name>`, verify it loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
