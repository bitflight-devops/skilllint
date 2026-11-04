"""Earlier coordinates must not survive a descendant symlink repair."""

from __future__ import annotations

from pathlib import Path

import pytest

from skilllint.plugin_validator import validate_file, validate_single_path, violations_to_result
from skilllint.scan_runtime import collect_validation_results
from skilllint.source_location import SourceLocation


@pytest.mark.parametrize("relative", [False, True])
def test_descendant_symlink_repair_clears_only_stale_source_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
) -> None:
    """A root-level fix changes only sources routed through the repaired link."""
    monkeypatch.chdir(tmp_path)
    root = Path("plugin") if relative else tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"name":"demo"}', encoding="utf-8")
    old, new, unrelated = (root / name for name in ("old ", "old", "unrelated"))
    before = "---\nname: demo\ndescription: A valid description.\n---\n# Body\n[missing](../../../missing.md)\n"
    after = before.replace("# Body\n", "# Body\n\nNew content.\n\n")
    for folder, content in ((old, before), (new, after), (unrelated, before)):
        (folder / "demo").mkdir(parents=True)
        (folder / "demo" / "SKILL.md").write_text(content, encoding="utf-8")
    alias = root / "skills"
    alias.symlink_to("old ", target_is_directory=True)
    source = alias / "demo" / "SKILL.md"
    other = unrelated / "demo" / "SKILL.md"
    original = old / "demo" / "SKILL.md"
    run = collect_validation_results(
        expanded_paths=[source, other, original, root, source],
        check=False,
        fix=True,
        verbose=True,
        platform_override=None,
        validate_single_path=validate_single_path,
        validate_file=validate_file,
        violations_to_result=violations_to_result,
        adapters={},
        include_gitignore=True,
    )
    assert alias.readlink() == Path("old")
    assert [(fix.path, fix.codes) for fix in run.fixes] == [(root, ("SL001",))]
    findings = [issue for _name, result in run.results[source] for issue in result.errors if issue.code == "LK001"]
    assert len(findings) == 2
    assert findings[0].source_location == SourceLocation(path=source)
    start = after.index("../../../missing.md")
    assert findings[1].source_location == SourceLocation.from_offsets(
        source, after, start, start + len("../../../missing.md")
    )
    for unchanged_source in (other, original):
        unchanged = [
            issue for _name, result in run.results[unchanged_source] for issue in result.errors if issue.code == "LK001"
        ]
        start = before.index("../../../missing.md")
        assert len(unchanged) == 1
        assert unchanged[0].source_location == SourceLocation.from_offsets(
            unchanged_source, before, start, start + len("../../../missing.md")
        )
    aggregate = [issue for _name, result in run.results[root] for issue in result.info if issue.code == "LK004"]
    assert len(aggregate) == 1
    assert aggregate[0].source_location == findings[1].source_location
