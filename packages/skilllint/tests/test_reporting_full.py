"""Source, display-cell, and terminal-safety contracts for human diagnostics."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.cells import cell_len
from rich.console import Console

from skilllint.models import ValidationIssue, ValidationResult
from skilllint.reporting_full import ColorMode, FullReporter, _excerpt_line, human_console
from skilllint.source_location import SourceLocation, SourcePosition, source_digest


def _issue(path: Path, content: str, start: int, end: int, **changes) -> ValidationIssue:
    return ValidationIssue(
        field="label",
        severity="error",
        code="LK001",
        message="Missing link",
        suggestion="Check the destination",
        docs_url="skilllint rule LK001",
        source_location=SourceLocation.from_offsets(path, content, start, end),
    ).model_copy(update=changes)


def _render(issue: ValidationIssue, *, width: int = 80, verbose: bool = False) -> str:
    output = io.StringIO()
    console = Console(file=output, width=width, height=24, force_terminal=False, markup=False)
    result = ValidationResult(passed=False, errors=[], warnings=[], info=[])
    getattr(result, {"error": "errors", "warning": "warnings", "info": "info"}[issue.severity]).append(issue)
    FullReporter(console).report({Path("aggregate"): [("links", result)]}, verbose=verbose)
    return output.getvalue()


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_real_source_range_and_original_path(tmp_path: Path, monkeypatch, newline: str) -> None:
    monkeypatch.chdir(tmp_path)
    path = Path("café.md")
    content = newline.join(["one", "é\t界😀 target", "last", ""])
    path.write_bytes(content.encode())
    first = content.index("target")
    output = _render(_issue(path, content, first, first + 6))
    assert " --> café.md:2:6" in output
    assert "aggregate" not in output
    assert "2 | é       界😀 target" in output
    source, marker = output.splitlines()[3:5]
    assert cell_len(source[: source.index("target")]) == marker.index("^")
    assert marker.count("^") == 6
    assert "help: Check the destination" in output
    assert "docs: skilllint rule LK001" in output


@pytest.mark.parametrize("problem", ["changed", "missing", "invalid-utf8", "no-digest", "out-of-bounds"])
def test_untrusted_source_is_file_only(tmp_path: Path, problem: str) -> None:
    path = tmp_path / "source.md"
    path.write_text("old content\n")
    issue = _issue(path, "old content\n", 0, 3)
    assert issue.source_location is not None
    if problem == "changed":
        path.write_text("new content\n")
    elif problem == "missing":
        path.unlink()
    elif problem == "invalid-utf8":
        path.write_bytes(b"\xff")
    elif problem == "no-digest":
        issue = issue.model_copy(
            update={"source_location": SourceLocation(path=path, start=SourcePosition(line=1, column=1))}
        )
    else:
        source = issue.source_location.model_copy(update={"start": SourcePosition(line=100, column=1), "end": None})
        issue = issue.model_copy(update={"source_location": source})
    output = _render(issue, width=200)
    assert str(path) in output
    assert "^" not in output
    assert "source.md:" not in output
    assert "old content" not in output
    assert "new content" not in output
    assert "Missing link" in output


def test_file_only_ignores_legacy_line(tmp_path: Path) -> None:
    issue = ValidationIssue(field="name", severity="error", code="FM001", message="missing", line=99)
    output = _render(issue)
    assert " --> aggregate\n" in output
    assert "99" not in output
    assert "^" not in output


@pytest.mark.parametrize("end_at_next_line", [False, True])
def test_multiline_half_open_ranges(tmp_path: Path, end_at_next_line: bool) -> None:
    content = "start here\nmiddle\nend here\nnot selected\n"
    path = tmp_path / "source.md"
    path.write_text(content)
    end = content.index("not selected") if end_at_next_line else content.index("end here") + 3
    output = _render(_issue(path, content, 6, end), width=200)
    assert "1 | start here" in output
    assert "3 | end here" in output
    assert " | …" in output
    assert "not selected" not in output
    assert "middle" not in output
    markers = [line for line in output.splitlines() if "^" in line]
    assert markers[0].endswith("^^^^")
    assert markers[1].count("^") == (8 if end_at_next_line else 3)


def test_point_at_eof_and_empty_line(tmp_path: Path) -> None:
    path = tmp_path / "source.md"
    path.write_text("line\n")
    output = _render(_issue(path, "line\n", 5, 5), width=200)
    assert "source.md:2:1" in output
    assert "2 | " in output
    assert output.count("^") == 1


@pytest.mark.parametrize("width", [8, 20, 80])
def test_long_source_viewport_has_aligned_highlight(width: int) -> None:
    line = "界" * 100 + "TARGET" + "tail" * 100
    excerpt = _excerpt_line(line, 100, 106, width=width, tab_size=8)
    assert excerpt is not None
    visible, indent, count = excerpt
    assert cell_len(visible) <= width
    assert visible.startswith("…")
    assert visible.endswith("…")
    if "TARGET" in visible:
        assert indent == cell_len(visible[: visible.index("TARGET")])
        assert count == 6
    assert count > 0
    assert indent + count <= width


def test_combining_marks_and_unicode_separators(tmp_path: Path) -> None:
    content = "e\N{COMBINING ACUTE ACCENT} 界 target\u2028tail"
    path = tmp_path / "source.md"
    path.write_text(content)
    start = content.index("target")
    output = _render(_issue(path, content, start, start + 6), width=200)
    source, marker = output.splitlines()[3:5]
    assert cell_len(source[: source.index("target")]) == marker.index("^")
    assert "\\u2028tail" in output


def test_terminal_controls_markup_and_emoji_are_literal(tmp_path: Path) -> None:
    content = "before\x1b[31m\t[red]:warning: target\x00"
    path = tmp_path / "source.md"
    path.write_text(content)
    start = content.index("target")
    issue = _issue(
        path,
        content,
        start,
        start + 6,
        message="[red]:warning:\x1b[2J\nforged",
        suggestion="\rhelp",
        docs_url="\x1b]8;;evil\x07",
    )
    output = _render(issue, width=200)
    assert "\x1b" not in output
    assert "\x00" not in output
    assert "[red]:warning:" in output
    assert "\\x1b[2J\\nforged" in output
    source, marker = output.splitlines()[3:5]
    assert cell_len(source[: source.index("target")]) == marker.index("^")
    assert "\\x00" in source


def test_info_hidden_unless_verbose_and_duplicate_findings_retained(tmp_path: Path) -> None:
    issue = _issue(Path("missing"), "", 0, 0, severity="info")
    assert "info[LK001]" not in _render(issue)
    assert "info[LK001]" in _render(issue, verbose=True)
    output = io.StringIO()
    result = ValidationResult(passed=False, errors=[issue, issue], warnings=[], info=[])
    FullReporter(Console(file=output)).report({tmp_path: [("test", result)]})
    assert output.getvalue().count("info[LK001]") == 2


@pytest.mark.parametrize("width", [1, 3, 6, 20])
def test_narrow_terminal_never_crashes_or_overflows_source(tmp_path: Path, width: int) -> None:
    path = tmp_path / "source.md"
    path.write_text("target")
    output = _render(_issue(path, "target", 0, 6), width=width)
    assert output
    for line in output.splitlines():
        assert cell_len(line) <= width


@pytest.mark.parametrize("mode", ["auto", "always", "never"])
def test_color_modes_in_redirected_stream(monkeypatch, mode: ColorMode) -> None:
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("NO_COLOR", "1")
    stream = io.StringIO()
    console = human_console(color=mode, file=stream)
    console.print("hello", style="bold red")
    assert ("\x1b[" in stream.getvalue()) == (mode == "always")
    stream = io.StringIO()
    human_console(color=mode, no_color=True, file=stream).print("hello", style="red")
    assert "\x1b" not in stream.getvalue()


def test_source_digest_is_not_a_public_field() -> None:
    source = SourceLocation.from_offsets(Path("source.md"), "content", 0, 3)
    assert source.content_digest == source_digest("content")
    assert "content_digest" not in source.model_dump()
    assert "content_digest" not in source.model_json_schema()["properties"]


def test_cropped_eof_and_last_character_never_mark_an_unrelated_glyph() -> None:
    excerpt = _excerpt_line("abcdef", 6, 6, width=6, tab_size=8)
    assert excerpt is not None
    visible, indent, count = excerpt
    assert indent == cell_len(visible)
    assert count == 1
    assert indent < 6
    excerpt = _excerpt_line("a" * 80, 79, 80, width=3, tab_size=8)
    assert excerpt is not None
    visible, indent, count = excerpt
    assert visible[indent] == "a"
    assert not visible.endswith("…")
    assert _excerpt_line("\t", 0, 1, width=3, tab_size=8) is None


@pytest.mark.parametrize("prefix", ["♥️", "👍🏽", "🇳🇿", "e\N{COMBINING ACUTE ACCENT}"])
def test_grapheme_clusters_remain_intact_and_aligned(prefix: str) -> None:
    excerpt = _excerpt_line(prefix + "X", len(prefix), len(prefix) + 1, width=80, tab_size=8)
    assert excerpt is not None
    visible, indent, count = excerpt
    assert visible == prefix + "X"
    assert indent == cell_len(prefix)
    assert count == 1
    cropped = _excerpt_line(prefix + "X", len(prefix), len(prefix) + 1, width=3, tab_size=8)
    assert cropped is not None
    assert cropped[0] in {prefix + "X", "…X"}


def test_range_inside_combining_sequence_marks_its_glyph() -> None:
    excerpt = _excerpt_line("e\N{COMBINING ACUTE ACCENT}X", 1, 2, width=80, tab_size=8)
    assert excerpt == ("e\N{COMBINING ACUTE ACCENT}X", 0, 1)


def test_report_reads_each_source_snapshot_once(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "source.md"
    path.write_text("first second")
    issues = [_issue(path, "first second", 0, 5), _issue(path, "first second", 6, 12)]
    read_text = Path.read_text
    reads = []

    def tracked_read(self, *args, **kwargs):
        reads.append(self)
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_read)
    result = ValidationResult(passed=False, errors=issues, warnings=[], info=[])
    FullReporter(Console(file=io.StringIO())).report({path: [("links", result)]})
    assert reads == [path]


def test_link_producer_hashes_source_once(tmp_path: Path, monkeypatch) -> None:
    from skilllint.rules import lk_series

    original = lk_series.source_digest
    hashes = []

    def tracked_digest(content):
        hashes.append(content)
        return original(content)

    monkeypatch.setattr(lk_series, "source_digest", tracked_digest)
    content = "[one](./missing-one.md) [two](./missing-two.md)"
    issues = lk_series.check_lk001(content, tmp_path / "SKILL.md")
    assert len(issues) == 2
    assert hashes == [content]
    assert all(issue.source_location is not None and issue.source_location.content_digest for issue in issues)


def test_orphan_combining_mark_is_visible_instead_of_marking_next_glyph() -> None:
    excerpt = _excerpt_line("\N{COMBINING ACUTE ACCENT}X", 0, 1, width=80, tab_size=8)
    assert excerpt == (r"\u0301X", 0, 6)
