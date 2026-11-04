"""Precise diagnostic source metadata without legacy output changes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from skilllint.frontmatter_yaml import frontmatter_source_locations
from skilllint.models import ValidationIssue
from skilllint.plugin_validator import _collect_validator_results, _issue_to_violation, violations_to_result
from skilllint.policy import IgnoreConfig, ValidationPolicy
from skilllint.rules.lk_series import check_lk001, check_lk004
from skilllint.source_location import SourceLocation, SourcePosition
from skilllint.validators.frontmatter import FrontmatterValidator, _coerce_validation_issues
from skilllint.validators.rule_series import InternalLinkValidator


def test_coordinates_count_unicode_characters_not_bytes_or_display_cells() -> None:
    """Emoji, combining marks and tabs each retain their Python string offsets."""
    content = "é😀e\u0301\tlink\r\nnext"
    assert SourcePosition.from_offset(content, content.index("link")) == SourcePosition(line=1, column=6)
    assert SourcePosition.from_offset(content, content.index("next")) == SourcePosition(line=2, column=1)
    assert SourcePosition.from_offset(content, len(content)) == SourcePosition(line=2, column=5)


@pytest.mark.parametrize("offset", [-1, 5])
def test_out_of_bounds_offsets_are_rejected(offset: int) -> None:
    """An invalid source offset must not become a plausible coordinate."""
    with pytest.raises(ValueError, match="within the source text"):
        SourcePosition.from_offset("text", offset)


@pytest.mark.parametrize("position", [{"line": 0, "column": 1}, {"line": 1, "column": -1}, {"line": True, "column": 1}])
def test_positions_reject_nonpositive_or_boolean_coordinates(position: dict[str, int]) -> None:
    """Coordinates are actual positive integer positions."""
    with pytest.raises(ValidationError):
        SourcePosition.model_validate(position)


def test_locations_distinguish_unknown_file_point_and_range() -> None:
    """Absence is explicit and an end is exclusive, never an invented line one."""
    issue = ValidationIssue(field="label", severity="error", message="bad", code="FM001")
    assert issue.source_location is None
    assert SourceLocation(path=Path("missing.md")).start is None
    start = SourcePosition(line=2, column=3)
    assert SourceLocation(path=Path("x.md"), start=start).end is None
    assert SourceLocation(path=Path("x.md"), start=start, end=start).end == start
    with pytest.raises(ValidationError, match="requires a start"):
        SourceLocation(path=Path("x.md"), end=start)
    with pytest.raises(ValidationError, match="must not precede"):
        SourceLocation(path=Path("x.md"), start=start, end=SourcePosition(line=1, column=9))


def test_source_metadata_preserves_legacy_dump_schema_and_format() -> None:
    """Existing JSON consumers and terminal output see exactly the same issue."""
    plain = ValidationIssue(field="description", severity="error", message="bad", code="FM005", line=3)
    located = plain.model_copy(update={"source_location": SourceLocation(path=Path("actual.md"))})
    assert located.model_dump() == plain.model_dump()
    assert json.loads(located.model_dump_json()) == json.loads(plain.model_dump_json())
    assert located.format() == plain.format()
    assert "source_location" not in ValidationIssue.model_json_schema()["properties"]
    assert "source_location" not in ValidationIssue.model_json_schema(mode="serialization")["properties"]
    assert _coerce_validation_issues([located])[0].source_location == located.source_location


def test_adapter_boundary_retains_location_separately_from_field() -> None:
    """A semantic field label never substitutes for the actual source path."""
    issue = ValidationIssue(
        field="internal-links",
        severity="error",
        message="bad",
        code="LK001",
        source_location=SourceLocation.from_offsets(Path("skills/demo/SKILL.md"), "é\tmissing", 2, 9),
    )
    result = violations_to_result([_issue_to_violation(issue)])
    assert result.errors[0].source_location == issue.source_location
    assert result.errors[0].field == "internal-links"
    assert result.errors[0].line is None


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_frontmatter_points_to_original_key_with_unicode_and_tabs(tmp_path: Path, newline: str) -> None:
    """YAML parser marks refer to the authored key, not a normalized value."""
    path = tmp_path / "SKILL.md"
    path.write_bytes(
        newline.join(["---", '{note: "é😀\ttext", name: Bad_Name, description: ok}', "---", "body"]).encode()
    )
    issue = next(issue for issue in FrontmatterValidator().validate(path).errors if issue.code == "FM010")
    assert issue.source_location == SourceLocation(
        path=path, start=SourcePosition(line=2, column=19), end=SourcePosition(line=2, column=23)
    )
    assert issue.line is None


def test_missing_frontmatter_field_has_file_identity_without_coordinates(tmp_path: Path) -> None:
    """A missing key cannot have a key span."""
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")
    issue = next(issue for issue in FrontmatterValidator().validate(path).errors if issue.code == "FM001")
    assert issue.source_location == SourceLocation(path=path)


@pytest.mark.parametrize("content", [None, b"\xff", b"body without frontmatter\n"])
def test_missing_unreadable_and_absent_frontmatter_sources_are_file_only(tmp_path: Path, content: bytes | None) -> None:
    """Neither unavailable bytes nor absent frontmatter justify a source line."""
    path = tmp_path / "SKILL.md"
    if content is not None:
        path.write_bytes(content)
    issue = FrontmatterValidator().validate(path).errors[0]
    assert issue.source_location == SourceLocation(path=path)


def test_yaml_syntax_error_has_original_parser_point(tmp_path: Path) -> None:
    """Syntax positions come from original text, not the recovery parser."""
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: demo\ndescription: ]\n---\nbody\n", encoding="utf-8")
    issue = FrontmatterValidator().validate(path).errors[0]
    assert issue.code == "FM002"
    assert issue.source_location == SourceLocation(path=path, start=SourcePosition(line=3, column=14))


def test_recovered_yaml_does_not_claim_transformed_coordinates(tmp_path: Path) -> None:
    """Quoting a value in memory never supplies marks for the original file."""
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: demo\ndescription: bad: value\n---\nbody\n", encoding="utf-8")
    issue = next(issue for issue in FrontmatterValidator().validate(path).warnings if issue.code == "FM009")
    assert issue.source_location == SourceLocation(path=path)


def test_duplicate_and_aliased_keys_have_no_ambiguous_key_spans() -> None:
    """Duplicate names and alias marks cannot identify a unique local key."""
    path = Path("SKILL.md")
    fields, _error = frontmatter_source_locations("name: first\nname: second\n", path, line_offset=1)
    assert "name" not in fields
    fields, _error = frontmatter_source_locations("key: &key name\n*key: value\n", path, line_offset=1)
    assert "name" not in fields


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_markdown_destinations_keep_original_positions_after_masking(tmp_path: Path, newline: str) -> None:
    """Code/comments, Unicode and duplicate destinations do not move spans."""
    path = tmp_path / "SKILL.md"
    content = newline.join([
        "```md",
        "[ignored](ignored.md)",
        "```",
        "<!-- hidden",
        "comment -->",
        "é😀\t`example` [first](missing.md) and [second](missing.md)",
        '[ref]: <missing%20file.md> "Title"',
        '<img src="missing&amp;image.png">',
    ])
    issues = check_lk001(content, path)
    assert len(issues) == 4
    expected = []
    offset = 0
    for destination in ("missing.md", "missing.md", "missing%20file.md", "missing&amp;image.png"):
        start = content.index(destination, offset)
        offset = start + len(destination)
        expected.append(SourceLocation.from_offsets(path, content, start, offset))
    assert [issue.source_location for issue in issues] == expected
    assert expected[0].start == SourcePosition(line=6, column=22)
    assert all(issue.line is None for issue in issues)


def test_inline_code_does_not_join_fragments_into_a_link(tmp_path: Path) -> None:
    """Masking must not turn separated Markdown fragments into a new link."""
    assert not check_lk001("[example]`not a link`(missing.md)", tmp_path / "SKILL.md")


def test_plugin_link_source_is_linking_file_not_validation_root(tmp_path: Path) -> None:
    """LK004 retains its legacy field/line while exposing the real source."""
    path = tmp_path / "agents" / "helper.md"
    content = "# Helper\nRead [guide](../guide.md).\n"
    issue = check_lk004(content, path, tmp_path)[0]
    assert issue.field == "agents/helper.md"
    assert issue.line == 2
    assert issue.source_location == SourceLocation.from_offsets(
        path, content, content.index("../guide.md"), content.index("../guide.md") + len("../guide.md")
    )


def test_severity_remapping_retains_source_locations(tmp_path: Path) -> None:
    """Policy changes severity, not diagnostic identity."""
    path = tmp_path / "SKILL.md"
    path.write_text("[guide](missing.md)\n", encoding="utf-8")
    results = _collect_validator_results(
        [InternalLinkValidator()],
        path,
        config_root=None,
        ignore_config=IgnoreConfig(),
        policy=ValidationPolicy(thresholds={}, ignore=IgnoreConfig(), severity={"LK001": "warning"}),
    )
    issue = results[0][1].warnings[0]
    assert issue.source_location == SourceLocation.from_offsets(path, "[guide](missing.md)\n", 8, 18)


def test_nonstandard_frontmatter_opener_does_not_invent_line_offset(tmp_path: Path) -> None:
    """Legacy parsing tolerance is not evidence of a standard delimiter line."""
    path = tmp_path / "SKILL.md"
    path.write_text("--- name: Bad_Name\ndescription: ok\n---\nbody\n", encoding="utf-8")
    issue = next(issue for issue in FrontmatterValidator().validate(path).errors if issue.code == "FM010")
    assert issue.source_location == SourceLocation(path=path)


@pytest.mark.parametrize("content", [None, b"\xff"])
def test_unavailable_markdown_source_has_file_only_location(tmp_path: Path, content: bytes | None) -> None:
    """Link validation retains a source identity even when no text can be read."""
    path = tmp_path / "SKILL.md"
    if content is not None:
        path.write_bytes(content)
    issue = InternalLinkValidator().validate(path).errors[0]
    assert issue.source_location == SourceLocation(path=path)


@pytest.mark.parametrize(
    "markup", ["[x](missing`x`.md)", "[x](<missing`x`.md>)", "[x]: missing`x`.md", '<a href="missing`x`.md">']
)
def test_backticks_in_destinations_are_literal_source_characters(tmp_path: Path, markup: str) -> None:
    """Inline-code masking must not erase or replace a filename's backticks."""
    path = tmp_path / "SKILL.md"
    destination = "missing`x`.md"
    issue = check_lk001(markup, path)[0]
    start = markup.index(destination)
    assert issue.source_location == SourceLocation.from_offsets(path, markup, start, start + len(destination))
    assert destination in issue.message
    (tmp_path / destination).write_text("exists", encoding="utf-8")
    assert not check_lk001(markup, path)


def test_inline_code_in_label_preserves_authored_label(tmp_path: Path) -> None:
    """Masking used for recognition must not leak padding into the message."""
    issue = check_lk001("[with `code` text](missing.md)", tmp_path / "SKILL.md")[0]
    assert "[with `code` text](missing.md)" in issue.message


@pytest.mark.parametrize("content", ["`[x](missing.md)`", '`<a href="missing.md">`', "[x](bad`spaces here`.md)"])
def test_code_wrapped_links_and_invalid_destinations_stay_ignored(tmp_path: Path, content: str) -> None:
    """Protecting literal destinations does not activate code examples."""
    assert not check_lk001(content, tmp_path / "SKILL.md")


def test_nested_schema_error_does_not_match_unrelated_dotted_key(tmp_path: Path) -> None:
    """Flattened schema labels are not proof of a literal top-level YAML key."""
    path = tmp_path / "agents" / "helper.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: helper\ndescription: ok\nmcpServers: bad\n"
        "mcpServers.list[any]: irrelevant\nmcpServers.dict[str,any]: irrelevant\n---\nbody\n",
        encoding="utf-8",
    )
    issues = [issue for issue in FrontmatterValidator().validate(path).errors if issue.field.startswith("mcpServers.")]
    assert len(issues) == 2
    assert all(issue.source_location == SourceLocation(path=path) for issue in issues)


def test_comment_delimiters_in_destination_are_literal(tmp_path: Path) -> None:
    """A comment-looking filename must not be erased by Markdown masking."""
    path = tmp_path / "SKILL.md"
    destination = "foo<!--x-->bar.md"
    content = f"[x]({destination})"
    issue = check_lk001(content, path)[0]
    assert destination in issue.message
    assert issue.source_location == SourceLocation.from_offsets(path, content, 4, 4 + len(destination))
    (tmp_path / destination).write_text("exists", encoding="utf-8")
    assert not check_lk001(content, path)
    assert not check_lk001("<!-- [x](missing.md) -->", path)


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_renames_rebase_aggregated_source_paths_without_rewriting_unrelated_paths(
    tmp_path: Path, severity: Literal["error", "warning", "info"]
) -> None:
    """Plugin result keys do not identify every source affected by a rename."""
    from skilllint.models import ValidationResult
    from skilllint.scan_runtime import _rebase_collected

    old, new = tmp_path / "Bad_Name", tmp_path / "bad-name"
    source = old / "references" / "guide.md"
    alias = tmp_path / "alias" / "guide.md"
    outside = tmp_path / "Bad_Name-other" / "guide.md"
    locations = [SourceLocation(path=path, start=SourcePosition(line=3, column=7)) for path in (source, alias, outside)]
    issues = [
        ValidationIssue(
            field="semantic-label", severity=severity, message="link", code="LK004", source_location=location
        )
        for location in locations
    ]
    result = ValidationResult(
        passed=severity != "error",
        errors=issues if severity == "error" else [],
        warnings=issues if severity == "warning" else [],
        info=issues if severity == "info" else [],
    )
    results = {tmp_path: [("plugin", result)]}
    identities = {source: source, alias: source, outside: outside, tmp_path: tmp_path}
    _rebase_collected(results, [], identities, old, new, canonical_old=old)
    relocated = results[tmp_path][0][1]
    found = [*relocated.errors, *relocated.warnings, *relocated.info]
    assert [issue.source_location.path for issue in found if issue.source_location is not None] == [
        new / "references" / "guide.md",
        new / "references" / "guide.md",
        outside,
    ]
    assert all(issue.field == "semantic-label" for issue in found)
    assert all(
        issue.source_location is not None and issue.source_location.start == locations[0].start for issue in found
    )


@pytest.mark.parametrize(("absolute_root", "absolute_skill"), [(True, True), (False, False)])
def test_fix_collection_keeps_aggregated_symlink_sources_after_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, absolute_root: bool, absolute_skill: bool
) -> None:
    """Source aliases are captured before the actual fixer leaves them dangling."""
    from skilllint.plugin_validator import validate_file, validate_single_path
    from skilllint.scan_runtime import collect_validation_results

    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"name":"demo"}', encoding="utf-8")
    old = tmp_path / "skills" / "Bad_Name"
    old.mkdir(parents=True)
    skill = old / "SKILL.md"
    skill.write_text("---\nname: Bad_Name\ndescription: valid description\n---\n# Body\n", encoding="utf-8")
    source = old / "guide.md"
    source.write_text("[outside](../../../outside.md)\n", encoding="utf-8")
    (tmp_path / "agents").mkdir()
    alias = tmp_path / "agents" / "alias.md"
    alias.symlink_to(source)
    monkeypatch.chdir(tmp_path)
    root_input = tmp_path if absolute_root else Path()
    skill_input = skill if absolute_skill else skill.relative_to(tmp_path)
    run = collect_validation_results(
        expanded_paths=[root_input, skill_input],
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
    issues = [issue for _name, result in run.results[root_input] for issue in result.info if issue.code == "LK004"]
    assert len(issues) == 2
    new_source = tmp_path / "skills" / "bad-name" / "guide.md"
    assert new_source.is_file()
    assert not alias.exists()
    assert all(
        issue.source_location is not None and issue.source_location.path.resolve() == new_source for issue in issues
    )


def test_unrelated_rename_does_not_change_alias_identity_basis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrelated source comparison cannot break a subsequent relative move."""
    from skilllint.models import ValidationResult
    from skilllint.scan_runtime import _rebase_collected

    monkeypatch.chdir(tmp_path)
    alias = Path("alias/notes.md")
    identity = Path("targetb/notes.md")
    issue = ValidationIssue(
        field="label", severity="info", message="link", code="LK004", source_location=SourceLocation(path=alias)
    )
    results = {alias: [("plugin", ValidationResult(passed=True, errors=[], warnings=[], info=[issue]))]}
    identities = {alias: identity}
    _rebase_collected(results, [], identities, Path("targeta"), Path("target-a"), canonical_old=Path("targeta"))
    assert identities[alias] == identity
    _rebase_collected(results, [], identities, Path("targetb"), Path("target-b"), canonical_old=Path("targetb"))
    moved = Path("target-b/notes.md")
    assert list(results) == [moved]
    assert results[moved][0][1].info[0].source_location == SourceLocation(path=moved)


@pytest.mark.parametrize("absolute_move", [False, True])
def test_source_and_move_can_use_different_path_bases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, absolute_move: bool
) -> None:
    """Location comparison uses one canonical basis without changing input routing."""
    from skilllint.models import ValidationResult
    from skilllint.scan_runtime import _rebase_collected

    monkeypatch.chdir(tmp_path)
    old = tmp_path / "old" if absolute_move else Path("old")
    new = tmp_path / "new" if absolute_move else Path("new")
    source = Path("old/notes.md") if absolute_move else tmp_path / "old/notes.md"
    issue = ValidationIssue(
        field="label", severity="info", message="link", code="LK004", source_location=SourceLocation(path=source)
    )
    results = {tmp_path: [("plugin", ValidationResult(passed=True, errors=[], warnings=[], info=[issue]))]}
    _rebase_collected(results, [], {source: source}, old, new, canonical_old=old)
    location = results[tmp_path][0][1].info[0].source_location
    assert location is not None
    assert location.path.absolute() == tmp_path / "new/notes.md"


@pytest.mark.parametrize("rename", [False, True])
def test_fix_invalidates_old_aggregate_spans_and_preserves_fresh_spans(tmp_path: Path, rename: bool) -> None:
    """A later YAML rewrite cannot leave an earlier body location pointing at another line."""
    from skilllint.plugin_validator import validate_file, validate_single_path
    from skilllint.scan_runtime import collect_validation_results

    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"name":"demo"}', encoding="utf-8")
    name = "Bad_Name" if rename else "demo"
    old = tmp_path / "skills" / name
    old.mkdir(parents=True)
    skill = old / "SKILL.md"
    skill.write_text(
        f"---\nname: {name}\ndescription: |\n  valid description\n  second line\n---\n"
        "# Body\n[outside](../../../outside.md)\n",
        encoding="utf-8",
    )
    run = collect_validation_results(
        expanded_paths=[tmp_path, skill],
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
    current = tmp_path / "skills" / ("bad-name" if rename else name) / "SKILL.md"
    aggregate = [issue for _name, result in run.results[tmp_path] for issue in result.info if issue.code == "LK004"]
    assert len(aggregate) == 1
    assert aggregate[0].source_location == SourceLocation(path=current)
    fresh = [issue for _name, result in run.results[current] for issue in result.errors if issue.code == "LK001"]
    assert len(fresh) == 1
    content = current.read_text(encoding="utf-8")
    start = content.index("../../../outside.md")
    assert fresh[0].source_location == SourceLocation.from_offsets(
        current, content, start, start + len("../../../outside.md")
    )


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
@pytest.mark.parametrize("operation", ["rename", "rewrite"])
def test_unrelated_fix_keeps_existing_result_models(
    tmp_path: Path, severity: Literal["error", "warning", "info"], operation: str
) -> None:
    """Every fix visits earlier results without copying unrelated or empty models."""
    from skilllint.models import AppliedFix, ValidationResult
    from skilllint.scan_runtime import _clear_changed_source_spans, _rebase_collected

    source = tmp_path / "other.md"
    location = SourceLocation(path=source, start=SourcePosition(line=2, column=3))
    issue = ValidationIssue(field="label", severity=severity, message="link", code="LK004", source_location=location)
    result = ValidationResult(
        passed=severity != "error",
        errors=[issue] if severity == "error" else [],
        warnings=[issue] if severity == "warning" else [],
        info=[issue] if severity == "info" else [],
    )
    empty = ValidationResult(passed=True, errors=[], warnings=[], info=[])
    results = {tmp_path: [("plugin", result), ("empty", empty)]}
    old, new = tmp_path / "old", tmp_path / "new"
    if operation == "rename":
        _rebase_collected(results, [], {source: source}, old, new, canonical_old=old)
    else:
        fix = AppliedFix(path=old / "SKILL.md", validator="frontmatter", codes=("FM004",), description="rewrite")
        _clear_changed_source_spans(results, [fix], {source: source})
    assert results[tmp_path][0][1] is result
    assert results[tmp_path][1][1] is empty
    assert issue.source_location == location


def test_many_destinations_and_code_spans_preserve_offsets(tmp_path: Path) -> None:
    """A large reference document does not require a destination scan per span."""
    from skilllint.rules.lk_series import _strip_code_blocks

    # The review's 12,000-link input exposed quadratic containment work.
    line = "[x](https://example.org) `sample` <!-- [hidden](ignored.md) -->\r\n"
    content = line * 12_000
    masked = "[x](https://example.org) " + " " * len("`sample` <!-- [hidden](ignored.md) -->") + "\r\n"
    assert _strip_code_blocks(content) == masked * 12_000
    assert check_lk001(content, tmp_path / "SKILL.md") == []
    assert check_lk004(content, tmp_path / "SKILL.md", tmp_path) == []


@pytest.mark.parametrize(
    "content",
    ['<a href="[inner](short)`literal`">', "[x]: [inner](short)`literal`\n", '[<a href="`literal`">](target.md)'],
)
def test_destination_index_preserves_nested_literal_delimiters(content: str) -> None:
    """The last-started destination need not have the largest containing end."""
    from skilllint.rules.lk_series import _strip_code_blocks

    assert _strip_code_blocks(content) == content


@pytest.mark.parametrize(
    "content",
    [
        "`x`[r]: missing.md",
        '[x](missing.md`code`"a title")',
        '[x](<missing.md>`code`"a title")',
        '[x]: <missing.md>`code`"a title"\n',
        '<a`code` href="missing.md">',
        '<a href`code`="missing.md">',
        '<a `code`href="missing.md">',
    ],
)
def test_masking_does_not_invent_link_separators(tmp_path: Path, content: str) -> None:
    """Padding cannot turn malformed original syntax into a real destination."""
    assert check_lk001(content, tmp_path / "SKILL.md") == []
    assert check_lk004(content, tmp_path / "SKILL.md", tmp_path) == []


@pytest.mark.parametrize(
    "content",
    [
        "[label `]` text](missing.md)",
        '[x](missing.md "a `code` title")',
        '<img alt="<!-- comment -->" src="missing.md">',
    ],
)
def test_authored_link_syntax_keeps_masked_label_and_unrelated_attributes(tmp_path: Path, content: str) -> None:
    """Checking syntax must not unmask labels or reject unrelated HTML content."""
    path = tmp_path / "SKILL.md"
    (issue,) = check_lk001(content, path)
    start = content.index("missing.md")
    assert issue.source_location == SourceLocation.from_offsets(path, content, start, start + len("missing.md"))
