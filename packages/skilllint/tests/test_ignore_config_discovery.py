"""Tests for .skilllint.json discovery and _resolve_ignore_config caching.

Covers:
- _load_skilllint_config: valid, missing, malformed, wrong shape
- _resolve_ignore_config: plugin root wins, .skilllint.json fallback, cache
  population, cache hit prevents re-walk, filesystem root fallback
- _is_suppressed: empty-string ("global") prefix
- validate_single_path: end-to-end suppression via .skilllint.json
"""

from __future__ import annotations

import json
from pathlib import Path

from skilllint.plugin_validator import (
    IgnoreConfig,
    _is_suppressed,
    _load_skilllint_config,
    _resolve_ignore_config,
    validate_single_path,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_SKILL = """\
---
name: smoke-skill
description: Use when testing smoke test scenarios for suppression.
version: "1.0.0"
---
# Smoke Skill

See [other file](other-file.md) for details.
"""


def _make_skill(directory: Path, name: str = "smoke-skill") -> Path:
    """Write a minimal SKILL.md that triggers LK002 (missing ./ prefix)."""
    directory.mkdir(parents=True, exist_ok=True)
    skill_file = directory / "SKILL.md"
    skill_file.write_text(_MINIMAL_SKILL, encoding="utf-8")
    return skill_file


def _make_plugin_root(directory: Path) -> Path:
    """Create a .claude-plugin/plugin.json marker so find_plugin_dir finds it."""
    plugin_dir = directory / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text('{"name": "test-plugin"}', encoding="utf-8")
    return directory


# ---------------------------------------------------------------------------
# _load_skilllint_config
# ---------------------------------------------------------------------------


def test_load_skilllint_config_valid_returns_ignore_mapping(tmp_path: Path) -> None:
    # Arrange
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"ignore": {"": ["LK002"], "skills/foo": ["AS008"]}}), encoding="utf-8")

    # Act
    result = _load_skilllint_config(cfg)

    # Assert
    assert result == {"": ["LK002"], "skills/foo": ["AS008"]}


def test_load_skilllint_config_missing_file_returns_empty(tmp_path: Path) -> None:
    result = _load_skilllint_config(tmp_path / ".skilllint.json")
    assert result == {}


def test_load_skilllint_config_malformed_json_returns_empty(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text("{not valid json", encoding="utf-8")
    assert _load_skilllint_config(cfg) == {}


def test_load_skilllint_config_ignore_not_dict_returns_empty(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"ignore": ["LK002"]}), encoding="utf-8")
    assert _load_skilllint_config(cfg) == {}


def test_load_skilllint_config_no_ignore_key_returns_empty(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"other": "stuff"}), encoding="utf-8")
    assert _load_skilllint_config(cfg) == {}


def test_load_skilllint_config_skips_non_list_values(tmp_path: Path) -> None:
    cfg = tmp_path / ".skilllint.json"
    cfg.write_text(json.dumps({"ignore": {"good": ["LK002"], "bad": "LK003"}}), encoding="utf-8")
    result = _load_skilllint_config(cfg)
    assert result == {"good": ["LK002"]}
    assert "bad" not in result


# ---------------------------------------------------------------------------
# _is_suppressed — empty-string global prefix
# ---------------------------------------------------------------------------


def test_is_suppressed_empty_prefix_matches_any_file(tmp_path: Path) -> None:
    # Arrange
    config: IgnoreConfig = {"": ["LK002"]}
    file_path = tmp_path / "subdir" / "SKILL.md"

    # Act / Assert
    assert _is_suppressed(config, file_path, tmp_path, "LK002") is True


def test_is_suppressed_empty_prefix_does_not_match_different_code(tmp_path: Path) -> None:
    config: IgnoreConfig = {"": ["LK002"]}
    file_path = tmp_path / "SKILL.md"
    assert _is_suppressed(config, file_path, tmp_path, "LK001") is False


def test_is_suppressed_prefix_match_exact(tmp_path: Path) -> None:
    config: IgnoreConfig = {"skills/foo": ["AS008"]}
    file_path = tmp_path / "skills" / "foo"
    assert _is_suppressed(config, file_path, tmp_path, "AS008") is True


def test_is_suppressed_prefix_match_child(tmp_path: Path) -> None:
    config: IgnoreConfig = {"skills/foo": ["AS008"]}
    file_path = tmp_path / "skills" / "foo" / "SKILL.md"
    assert _is_suppressed(config, file_path, tmp_path, "AS008") is True


def test_is_suppressed_prefix_no_partial_segment_match(tmp_path: Path) -> None:
    # "skills/foo" must not match "skills/foobar/SKILL.md"
    config: IgnoreConfig = {"skills/foo": ["AS008"]}
    file_path = tmp_path / "skills" / "foobar" / "SKILL.md"
    assert _is_suppressed(config, file_path, tmp_path, "AS008") is False


# ---------------------------------------------------------------------------
# _resolve_ignore_config
# ---------------------------------------------------------------------------


def test_resolve_ignore_config_finds_skilllint_json(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# x", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    # Act
    config, root = _resolve_ignore_config(skill_file, cache)

    # Assert
    assert config == {"": ["LK002"]}
    assert root == tmp_path


def test_resolve_ignore_config_plugin_root_wins_over_skilllint_json_at_same_dir(tmp_path: Path) -> None:
    """When .claude-plugin/plugin.json and .skilllint.json are at the same directory,
    the plugin root check runs first so plugin config is used."""
    # Arrange — both markers at tmp_path level
    _make_plugin_root(tmp_path)
    (tmp_path / ".claude-plugin" / "validator.json").write_text(
        json.dumps({"ignore": {"": ["FM010"]}}), encoding="utf-8"
    )
    # .skilllint.json at the same level — should be ignored because plugin.json wins
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# x", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    # Act
    config, root = _resolve_ignore_config(skill_file, cache)

    # Assert: plugin root wins, so FM010 is suppressed (not LK002)
    assert root == tmp_path
    assert config == {"": ["FM010"]}


def test_resolve_ignore_config_returns_empty_when_nothing_found(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# x", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    config, root = _resolve_ignore_config(skill_file, cache)

    assert config == {}
    assert root is None


def test_resolve_ignore_config_populates_cache_for_walked_dirs(tmp_path: Path) -> None:
    """All directories in the walk chain are cached after the first call."""
    # Arrange
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    skill_file = nested / "SKILL.md"
    skill_file.write_text("# x", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    # Act — first call walks up three levels
    _resolve_ignore_config(skill_file, cache)

    # Assert — all walked directories are now in the cache
    assert str(nested.resolve()) in cache
    assert str((tmp_path / "a" / "b").resolve()) in cache
    assert str((tmp_path / "a").resolve()) in cache


def test_resolve_ignore_config_cache_hit_returns_same_result(tmp_path: Path) -> None:
    """Second call for same directory returns cached value without re-walking."""
    # Arrange
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# x", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    config1, root1 = _resolve_ignore_config(skill_file, cache)

    # Mutate the file to prove the cache is returned, not re-read
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["AS008"]}}), encoding="utf-8")

    config2, root2 = _resolve_ignore_config(skill_file, cache)

    assert config1 == config2 == {"": ["LK002"]}
    assert root1 == root2


def test_resolve_ignore_config_sibling_files_share_cache(tmp_path: Path) -> None:
    """Two files in the same directory reuse the cached result."""
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    file_a = tmp_path / "SKILL_A.md"
    file_b = tmp_path / "SKILL_B.md"
    file_a.write_text("# a", encoding="utf-8")
    file_b.write_text("# b", encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    config_a, root_a = _resolve_ignore_config(file_a, cache)
    config_b, root_b = _resolve_ignore_config(file_b, cache)

    assert config_a == config_b == {"": ["LK002"]}
    assert root_a == root_b == tmp_path
    # Cache should have exactly one entry (the shared directory)
    assert len(cache) == 1


# ---------------------------------------------------------------------------
# validate_single_path — end-to-end suppression via .skilllint.json
# ---------------------------------------------------------------------------


def test_validate_single_path_lk002_suppressed_by_skilllint_json(tmp_path: Path) -> None:
    """LK002 is not reported when .skilllint.json suppresses it globally."""
    # Arrange
    skill_dir = tmp_path / "smoke-skill"
    skill_file = _make_skill(skill_dir)
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")

    # Act
    results = validate_single_path(skill_file, check=True, fix=False, verbose=False)

    # Assert — flatten all issues across all validators
    all_codes = {
        str(issue.code)
        for validator_results in results.values()
        for _, vr in validator_results
        for issue in (vr.errors + vr.warnings + vr.info)
    }
    assert "LK002" not in all_codes, f"LK002 should have been suppressed, but got codes: {all_codes}"


def test_validate_single_path_lk002_not_suppressed_without_config(tmp_path: Path) -> None:
    """LK002 is reported normally when no .skilllint.json is present."""
    # Arrange
    skill_dir = tmp_path / "smoke-skill"
    skill_file = _make_skill(skill_dir)
    # No .skilllint.json written

    # Act
    results = validate_single_path(skill_file, check=True, fix=False, verbose=False)

    # Assert — LK002 must appear
    all_codes = {
        str(issue.code)
        for validator_results in results.values()
        for _, vr in validator_results
        for issue in (vr.errors + vr.warnings + vr.info)
    }
    assert "LK002" in all_codes, f"LK002 should have been reported, but got codes: {all_codes}"


def test_validate_single_path_path_prefix_suppression(tmp_path: Path) -> None:
    """A prefix-keyed suppress only silences the matching subtree."""
    # Arrange: .skilllint.json suppresses LK002 only under "skills/inner"
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"skills/inner": ["LK002"]}}), encoding="utf-8")
    inner_dir = tmp_path / "skills" / "inner"
    outer_dir = tmp_path / "skills" / "outer"
    inner_file = _make_skill(inner_dir)
    outer_file = _make_skill(outer_dir)

    def _lk002_codes(path: Path) -> set[str]:
        results = validate_single_path(path, check=True, fix=False, verbose=False)
        return {
            str(issue.code)
            for validator_results in results.values()
            for _, vr in validator_results
            for issue in (vr.errors + vr.warnings + vr.info)
            if str(issue.code) == "LK002"
        }

    # Assert inner: suppressed
    assert _lk002_codes(inner_file) == set()
    # Assert outer: not suppressed
    assert "LK002" in _lk002_codes(outer_file)


def test_validate_single_path_per_run_cache_shared_across_calls(tmp_path: Path) -> None:
    """per_run_cache is populated and reused across multiple validate_single_path calls."""
    # Arrange
    skill_dir = tmp_path / "smoke-skill"
    skill_file = _make_skill(skill_dir)
    (tmp_path / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["LK002"]}}), encoding="utf-8")
    cache: dict[str, tuple[IgnoreConfig, Path | None]] = {}

    # Act — two calls share the same cache
    validate_single_path(skill_file, check=True, fix=False, verbose=False, per_run_cache=cache)
    assert len(cache) > 0, "Cache should be populated after first call"

    # Corrupt the file to prove second call uses cache, not re-reads config
    (tmp_path / ".skilllint.json").write_text("{bad json}", encoding="utf-8")
    results = validate_single_path(skill_file, check=True, fix=False, verbose=False, per_run_cache=cache)

    all_codes = {
        str(issue.code)
        for validator_results in results.values()
        for _, vr in validator_results
        for issue in (vr.errors + vr.warnings + vr.info)
    }
    # LK002 should still be suppressed because the cache is used
    assert "LK002" not in all_codes
