"""Focused coverage for Issue #5's bounded JSON policy contract.

Threshold literals in these tests are chosen to exercise specific branches, not
to model real skills:
  - ``0`` and negative values exercise the positive-integer guard.
  - Distinct positive values (e.g. 12, 34, 99) exercise first-match precedence
    and cache stability; the exact numbers are arbitrary and unrelated to the
    real DEFAULT_THRESHOLDS (SK006=4400, SK007=8800).
  - ``1`` exercises unknown-rule filtering.
  - Reversed/equal pairs (9000 vs default SK007=8800) exercise the ordering guard.
"""

from __future__ import annotations

import json
from pathlib import Path

from skilllint.plugin_validator import DEFAULT_THRESHOLDS, ValidationPolicy, _load_policy, _resolve_policy


def test_policy_defaults_and_invalid_values_report_and_default(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"SK006": 0, "SK007": "bad"}, "severity": {"SK007": "error"}}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert policy.severity == {}
    # Every rejected entry is surfaced, not silently swallowed.
    assert len(diagnostics) == 3  # SK006=0, SK007="bad", severity SK007="error"


def test_policy_first_match_and_cache(tmp_path: Path) -> None:
    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"SK006": 12}}))
    child = tmp_path / "skills" / "demo"
    child.mkdir(parents=True)
    skill = child / "SKILL.md"
    skill.write_text("body")
    cache: dict[str, tuple[ValidationPolicy, Path | None]] = {}
    first, root = _resolve_policy(skill, cache)
    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"SK006": 99}}))
    second, second_root = _resolve_policy(skill, cache)
    assert first.thresholds["SK006"] == second.thresholds["SK006"] == 12
    assert root == second_root == tmp_path


def test_policy_plugin_precedes_project_without_merge(tmp_path: Path) -> None:
    # Project sets SK006=12; plugin sets a full valid pair. Precedence (no merge)
    # is proven by the project's SK006=12 NOT leaking into the plugin-resolved
    # policy — SK006 must be the plugin's value, not the project's.
    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"SK006": 12}}))
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}")
    (root / ".claude-plugin" / "validator.json").write_text(json.dumps({"thresholds": {"SK006": 34, "SK007": 56}}))
    skill = root / "SKILL.md"
    skill.write_text("body")
    policy, config_root = _resolve_policy(skill, {})
    assert policy.thresholds["SK006"] == 34  # plugin value, not project's 12 (no merge)
    assert policy.thresholds["SK007"] == 56
    assert config_root == root


def test_policy_ignore_retains_existing_shape(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"ignore": {"skills/demo": ["SK006"], "bad": "skip"}}))
    policy, _diagnostics = _load_policy(cfg)
    assert policy.ignore == {"skills/demo": ["SK006"]}


def test_unknown_policy_rules_are_ignored(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"NOPE": 1}, "severity": {"NOPE": "info"}}))
    policy, diagnostics = _load_policy(cfg)
    assert "NOPE" not in policy.thresholds
    assert "NOPE" not in policy.severity
    assert len(diagnostics) == 2


def test_malformed_policy_reports_and_defaults(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text("not json")
    policy, diagnostics = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert policy.ignore == {}
    assert len(diagnostics) == 1


def test_as005_is_not_a_configurable_threshold(tmp_path: Path) -> None:
    # AS005 shares the SK006/SK007 token band and has no threshold plumbing of
    # its own, so an AS005 threshold key is rejected (PR #97 review finding #1).
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"AS005": 1000}}))
    policy, diagnostics = _load_policy(cfg)
    assert "AS005" not in policy.thresholds
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert len(diagnostics) == 1


def test_as005_severity_is_configurable(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"severity": {"AS005": "info"}}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.severity == {"AS005": "info"}
    assert diagnostics == []


def test_inverted_thresholds_reset_to_defaults(tmp_path: Path) -> None:
    # SK006 >= SK007 makes the warning band unreachable; reset both (finding #2).
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"SK006": 9000}}))  # >= default SK007 (8800)
    policy, diagnostics = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert any("must be below SK007" in d for d in diagnostics)


def test_equal_thresholds_reset_to_defaults(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"SK006": 5000, "SK007": 5000}}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert any("must be below SK007" in d for d in diagnostics)


def test_composite_severity_value_does_not_crash(tmp_path: Path) -> None:
    # A list/dict severity value must be rejected, not raise TypeError on the
    # set membership check (finding #3 — trust-boundary crash).
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"severity": {"SK006": [], "SK007": {"nested": 1}}}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.severity == {}
    assert len(diagnostics) == 2


def test_policy_cache_reuses_ancestor_across_siblings(tmp_path: Path) -> None:
    # Codex re-review #1: a sibling skill must reuse an already-cached ancestor
    # instead of re-walking, re-reading config, and re-emitting diagnostics.
    # Config is deliberately invalid so diagnostics are observable.
    import contextlib
    import io

    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"AS005": 1000}}))
    a = tmp_path / "skills" / "a" / "SKILL.md"
    b = tmp_path / "skills" / "b" / "SKILL.md"
    b.parent.mkdir(parents=True, exist_ok=False)
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text("body")
    b.write_text("body")
    cache: dict[str, tuple[ValidationPolicy, Path | None]] = {}
    _resolve_policy(a, cache)
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        _resolve_policy(b, cache)  # second sibling — must NOT re-emit
    # The only cached ancestor (the shared "skills" dir + config root) is reused,
    # so no config re-read and no second diagnostic emission on stderr.
    assert "AS005 is not a configurable threshold" not in buf.getvalue()


def test_non_object_thresholds_section_is_reported(tmp_path: Path) -> None:
    # Codex re-review #1 (4a33171): a mistyped section like "thresholds": []
    # must produce a diagnostic, not silently default.
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": []}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert any("thresholds is not an object" in d for d in diagnostics)


def test_non_object_severity_section_is_reported(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"severity": "info"}))
    policy, diagnostics = _load_policy(cfg)
    assert policy.severity == {}
    assert any("severity is not an object" in d for d in diagnostics)


def test_platform_path_reuses_policy_cache_across_files(tmp_path: Path) -> None:
    # Codex re-review #2 (4a33171): --platform scans must reuse the per-run
    # cache so a 1000-file scan doesn't re-read config / re-emit per file.
    import contextlib
    import io

    from skilllint.plugin_validator import validate_file

    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"AS005": 1000}}))
    a = tmp_path / "skills" / "a" / "SKILL.md"
    b = tmp_path / "skills" / "b" / "SKILL.md"
    a.parent.mkdir(parents=True)
    b.parent.mkdir(parents=True, exist_ok=True)
    for f in (a, b):
        f.write_text("---\nname: x\ndescription: y\n---\nbody")
    cache: dict[str, tuple[ValidationPolicy, Path | None]] = {}
    validate_file(a, {}, policy_cache=cache)
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        validate_file(b, {}, policy_cache=cache)
    assert "AS005 is not a configurable threshold" not in buf.getvalue()
