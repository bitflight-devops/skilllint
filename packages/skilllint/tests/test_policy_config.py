"""Focused coverage for Issue #5's bounded JSON policy contract."""

from __future__ import annotations

import json
from pathlib import Path

from skilllint.plugin_validator import DEFAULT_THRESHOLDS, ValidationPolicy, _load_policy, _resolve_policy


def test_policy_defaults_and_invalid_values_fail_open(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"SK006": 0, "SK007": "bad"}, "severity": {"SK007": "error"}}))
    policy = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert policy.severity == {}


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
    (tmp_path / ".skilllint.json").write_text(json.dumps({"thresholds": {"SK006": 12}}))
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}")
    (root / ".claude-plugin" / "validator.json").write_text(json.dumps({"thresholds": {"SK007": 34}}))
    skill = root / "SKILL.md"
    skill.write_text("body")
    policy, config_root = _resolve_policy(skill, {})
    assert policy.thresholds["SK006"] == DEFAULT_THRESHOLDS["SK006"]
    assert policy.thresholds["SK007"] == 34
    assert config_root == root


def test_policy_ignore_retains_existing_shape(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"ignore": {"skills/demo": ["SK006"], "bad": "skip"}}))
    assert _load_policy(cfg).ignore == {"skills/demo": ["SK006"]}


def test_unknown_policy_rules_are_ignored(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"thresholds": {"NOPE": 1}, "severity": {"NOPE": "info"}}))
    policy = _load_policy(cfg)
    assert "NOPE" not in policy.thresholds
    assert "NOPE" not in policy.severity


def test_malformed_policy_fails_open(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text("not json")
    policy = _load_policy(cfg)
    assert policy.thresholds == DEFAULT_THRESHOLDS
    assert policy.ignore == {}
