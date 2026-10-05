"""Unit tests for skilllint.record_export."""

from __future__ import annotations

import html
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from rich.console import Console

from skilllint.record_export import build_svg_title, export_recording, make_recording_console

if TYPE_CHECKING:
    from collections.abc import Callable


class TestMakeRecordingConsole:
    """Tests for make_recording_console."""

    def test_returns_console_with_record_true(self) -> None:
        """make_recording_console returns a Console with record=True."""
        console = make_recording_console()
        assert isinstance(console, Console)
        # Rich exposes the flag as the public attribute ``record``
        assert console.record

    def test_returns_console_with_force_terminal(self) -> None:
        """make_recording_console sets force_terminal so ANSI codes are emitted."""
        console = make_recording_console()
        # force_terminal=True causes Rich to report the console as a terminal
        assert console.is_terminal

    def test_no_color_false_by_default(self) -> None:
        """no_color defaults to False."""
        console = make_recording_console()
        assert not console.no_color

    def test_no_color_true_disables_color(self) -> None:
        """Passing no_color=True disables colour output."""
        console = make_recording_console(no_color=True)
        assert console.no_color


class TestBuildSvgTitle:
    """Tests for build_svg_title."""

    def test_prefixes_skilllint_when_absent(self) -> None:
        """build_svg_title prepends 'skilllint' when first element is not 'skilllint'."""
        result = build_svg_title(["check", "plugins/"])
        assert result == "skilllint check plugins/"

    def test_does_not_double_prefix(self) -> None:
        """build_svg_title does not prepend 'skilllint' when already present."""
        result = build_svg_title(["skilllint", "check", "plugins/"])
        assert result == "skilllint check plugins/"

    def test_joins_with_spaces(self) -> None:
        """build_svg_title joins argv elements with a single space."""
        result = build_svg_title(["rules", "--fix", "path/to/plugin"])
        assert result == "skilllint rules --fix path/to/plugin"

    def test_empty_argv_returns_skilllint(self) -> None:
        """build_svg_title with empty list returns just 'skilllint'."""
        result = build_svg_title([])
        assert result == "skilllint"

    def test_single_element_skilllint(self) -> None:
        """build_svg_title with ['skilllint'] returns 'skilllint'."""
        result = build_svg_title(["skilllint"])
        assert result == "skilllint"

    def test_single_non_skilllint_element(self) -> None:
        """build_svg_title with a single non-skilllint element prefixes correctly."""
        result = build_svg_title(["check"])
        assert result == "skilllint check"


class TestExportRecording:
    """Tests for export_recording."""

    def _make_console_with_output(self) -> Console:
        """Return a recording console with some output captured."""
        console = make_recording_console()
        console.print("Hello, world!")
        return console

    def test_svg_written_for_svg_suffix(self, tmp_path: Path) -> None:
        """export_recording writes an SVG file when path has .svg suffix."""
        console = self._make_console_with_output()
        dest = tmp_path / "output.svg"
        export_recording(console, dest, title="test title")
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert content.strip().startswith("<svg")

    def test_html_written_for_html_suffix(self, tmp_path: Path) -> None:
        """export_recording writes an HTML file when path has .html suffix."""
        console = self._make_console_with_output()
        dest = tmp_path / "output.html"
        export_recording(console, dest, title="test title")
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<html" in content.lower()

    def test_html_suffix_case_insensitive(self, tmp_path: Path) -> None:
        """export_recording treats .HTML suffix as HTML format."""
        console = self._make_console_with_output()
        dest = tmp_path / "output.HTML"
        export_recording(console, dest, title="test title")
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<html" in content.lower()

    def test_atomic_write_no_partial_file_on_failure(self, tmp_path: Path) -> None:
        """export_recording leaves no partial file when export raises mid-write."""
        console = self._make_console_with_output()
        dest = tmp_path / "output.svg"

        # Patch os.replace to raise after the temp file is written, simulating
        # a failure between the temp-write and the rename.

        def failing_replace(src: str, dst: str | Path) -> None:
            # Remove the temp file manually to simulate a cleanup failure path,
            # then raise to abort.
            Path(src).unlink()
            raise OSError("simulated replace failure")

        with (
            patch("skilllint.record_export.os.replace", side_effect=failing_replace),
            pytest.raises(OSError, match="simulated replace failure"),
        ):
            export_recording(console, dest, title="test title")

        # The destination file must not exist.
        assert not dest.exists()

    def test_svg_title_appears_in_output(self, tmp_path: Path) -> None:
        """The title argument appears in the SVG output.

        Rich encodes spaces in SVG text nodes as the non-breaking space
        entity ``&#160;`` (which HTML-unescapes to the Unicode non-breaking
        space U+00A0).  We normalise all whitespace variants to ASCII space
        before asserting so the test is robust against Rich's encoding choice.
        """
        console = self._make_console_with_output()
        dest = tmp_path / "output.svg"
        export_recording(console, dest, title="My Custom Title")
        content = dest.read_text(encoding="utf-8")
        # Decode HTML entities then normalise non-breaking spaces to regular spaces.
        normalised = html.unescape(content).replace("\xa0", " ")
        assert "My Custom Title" in normalised

    def test_svg_output_has_no_trailing_whitespace(self, tmp_path: Path) -> None:
        """export_recording strips trailing whitespace from every line of SVG output.

        Rich's SVG export template contains structurally indented lines with
        trailing whitespace (independent of the recorded terminal content).
        The `trailing-whitespace` pre-commit/prek hook rewrites any such line
        when a screenshot is regenerated, so the file skilllint writes must
        already be clean or every regeneration trips the hook on first push.
        """
        console = self._make_console_with_output()
        dest = tmp_path / "output.svg"
        export_recording(console, dest, title="test title")
        content = dest.read_text(encoding="utf-8")
        offending = [line for line in content.splitlines() if line != line.rstrip()]
        assert not offending, f"lines with trailing whitespace: {offending!r}"

    def test_unsupported_extension_raises_value_error(self, tmp_path: Path) -> None:
        """export_recording raises ValueError for unsupported file extensions."""
        console = make_recording_console()
        console.print("hello")
        dest = tmp_path / "output.txt"
        with pytest.raises(ValueError, match="Unsupported file extension"):
            export_recording(console, dest, title="test")
        assert not dest.exists(), "No file should be created when extension is invalid"


def _render_check(console: Console) -> None:
    from skilllint.models import ValidationIssue, ValidationResult
    from skilllint.reporting import ConsoleReporter

    issue = ValidationIssue(field="name", severity="error", message="broken", code="AB001", suggestion="fix it")
    results = {Path("a.md"): [("V", ValidationResult(passed=False, errors=[issue], warnings=[], info=[]))]}
    reporter = ConsoleReporter(console)
    reporter.report(results, verbose=False, show_progress=True)
    reporter.summarize(1, 0, 1, 0)


def _render_rules(console: Console) -> None:
    from skilllint.plugin_validator import _show_rules_list

    _show_rules_list(console=console)
    console.print("\n[dim]Run [bold]skilllint rule [yellow]RULE_ID[/yellow][/bold] for details.[/dim]")


def _render_rule(console: Console) -> None:
    from skilllint.plugin_validator import _show_rule_doc

    _show_rule_doc("FM010", console=console)


class TestRecordingFile:
    """The ``file`` argument changes where output goes, never what is recorded."""

    @pytest.mark.parametrize("render", [_render_check, _render_rules, _render_rule], ids=lambda f: f.__name__)
    @pytest.mark.parametrize("suffix", [".svg", ".html"])
    def test_export_is_byte_equal_for_stdout_and_a_buffer(
        self, render: Callable[[Console], None], suffix: str, tmp_path: Path
    ) -> None:
        """Rendering into a buffer exports the same bytes as rendering to stdout."""
        to_stdout = tmp_path / f"stdout{suffix}"
        to_buffer = tmp_path / f"buffer{suffix}"
        stdout_console = make_recording_console()
        buffer_console = make_recording_console(file=StringIO())

        render(stdout_console)
        render(buffer_console)
        export_recording(stdout_console, to_stdout, title="t")
        export_recording(buffer_console, to_buffer, title="t")

        assert to_buffer.read_bytes() == to_stdout.read_bytes()

    def test_nothing_reaches_stdout_when_a_buffer_is_given(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The buffer receives the render; stdout stays empty."""
        buffer = StringIO()
        console = make_recording_console(file=buffer)

        _render_check(console)

        assert capsys.readouterr().out == ""
        assert "broken" in buffer.getvalue()

    def test_default_file_is_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Without ``file`` the console prints to stdout, as before."""
        _render_check(make_recording_console())

        assert "broken" in capsys.readouterr().out
