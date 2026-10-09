"""Diagnostic data reaches the terminal literally, never as a Rich emoji.

Rich replaces ``:name:`` with an emoji unless the print turns that off. The line number in
``field:LINE:`` is the visible case (``:100:`` renders as an emoji, ``:3:`` does not), but any
text the user controls (a path, a field, a message, a URL, a rule id) can hold ``:name:`` too.
``rich.markup.escape`` protects ``[`` only, so it cannot close this. Every surface that prints
data must keep emoji replacement off for that data.
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from cli_probe import Sandbox, run_cli
from hypothesis import example, given, strategies as st
from rich.cells import cell_len
from rich.console import Console
from rich.emoji import Emoji
from rich.panel import Panel

from skilllint import plugin_validator
from skilllint.output import print_panel
from skilllint.plugin_validator import AppliedFix, ErrorCode, ValidationIssue, ValidationResult
from skilllint.record_export import make_recording_console
from skilllint.reporting import ConsoleReporter

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture
    from typer.testing import CliRunner

ANSI: Final = re.compile(r"\x1b\[[0-9;]*m")
"""SGR colour sequences, which Rich writes around styled spans."""

EMOJI_LINES: Final = (100, 1234)
"""Line numbers that are also Rich emoji codes (``:100:`` and ``:1234:``), per issue #327."""

LINE_100_PLUGIN_FILE: Final = "skills/demo/SKILL.md"
"""Skill file whose out-of-plugin link (LK004) sits on line 100."""


def plain(text: str) -> str:
    """Return *text* without colour sequences."""
    return ANSI.sub("", text)


def capture_console(*, force_terminal: bool) -> tuple[Console, StringIO]:
    """Return a Rich console writing to an in-memory buffer, as a caller that injects one would."""
    buffer = StringIO()
    return Console(file=buffer, force_terminal=force_terminal, width=200, soft_wrap=True), buffer


def issue_on_line(
    line: int, *, field: str = "description", message: str = "Missing required field"
) -> ValidationResult:
    """Build a failing result holding one error that sits on *line*."""
    return ValidationResult(
        passed=False,
        errors=[ValidationIssue(field=field, severity="error", message=message, code=ErrorCode.FM001, line=line)],
        warnings=[],
        info=[],
    )


def report_text(results: dict[Path, list[tuple[str, ValidationResult]]], *, force_terminal: bool = True) -> str:
    """Report *results* through ConsoleReporter on an injected console and return the plain text."""
    console, buffer = capture_console(force_terminal=force_terminal)
    ConsoleReporter(console=console).report(results)
    return plain(buffer.getvalue())


class TestLineNumberIsLiteral:
    """The number after ``field:`` is printed as digits for every line number."""

    @pytest.mark.parametrize("line", [*EMOJI_LINES, 3])
    def test_report_emoji_code_line_number_prints_digits(self, line: int) -> None:
        """A line number that is also an emoji code prints as that number."""
        text = report_text({Path("SKILL.md"): [("FrontmatterValidator", issue_on_line(line))]})

        assert f"description:{line}: Missing required field" in text

    @given(line=st.integers(min_value=1))
    @example(line=100)
    @example(line=1234)
    def test_report_any_line_number_prints_digits(self, line: int) -> None:
        """Property: the printed location is ``field:LINE:`` for every line number."""
        text = report_text({Path("SKILL.md"): [("FrontmatterValidator", issue_on_line(line))]})

        assert f"description:{line}: Missing required field" in text


class TestEveryDataFieldIsLiteral:
    """Every user-controlled string in a diagnostic survives emoji replacement."""

    @given(name=st.from_regex(r"[a-z0-9_+]+", fullmatch=True))
    @example(name="smile")
    @example(name="100")
    @example(name="warning")
    def test_report_emoji_code_in_each_field_prints_literally(self, name: str) -> None:
        """A ``:name:`` token in path, validator, field, message, suggestion or url is not replaced."""
        token = f":{name}:"
        issue = ValidationIssue(
            field=f"f{token}",
            severity="error",
            message=f"m{token}",
            code=ErrorCode.FM001,
            line=7,
            suggestion=f"s{token}",
            docs_url=f"https://example.invalid/{token}",
        )
        result = ValidationResult(passed=False, errors=[issue], warnings=[], info=[])

        text = report_text({Path(f"p{token}/SKILL.md"): [(f"v{token}", result)]})

        for expected in (f"p{token}/SKILL.md", f"v{token}:", f"f{token}:7: m{token}", f"s{token}", f"/{token}"):
            assert expected in text

    def test_report_passed_progress_line_prints_path_literally(self) -> None:
        """The ``PASSED`` progress line does not turn a ``:100:`` in the path into an emoji."""
        console, buffer = capture_console(force_terminal=True)
        passing = ValidationResult(passed=True, errors=[], warnings=[], info=[])

        ConsoleReporter(console=console).report({Path("a:100:/SKILL.md"): [("V:100:", passing)]}, show_progress=True)

        assert "a:100:/SKILL.md" in plain(buffer.getvalue())

    def test_report_fixes_prints_path_codes_and_description_literally(self) -> None:
        """The ``--fix`` summary keeps ``:100:`` in every field it prints."""
        console, buffer = capture_console(force_terminal=True)
        fix = AppliedFix(
            path=Path("a:100:/SKILL.md"), validator="V:100:", codes=("FM:100:",), description="moved to line :100:"
        )

        ConsoleReporter(console=console).report_fixes([fix])

        text = plain(buffer.getvalue())
        for expected in ("a:100:/SKILL.md", "[FM:100:]", "V:100::", "moved to line :100:"):
            assert expected in text


class TestSurfaceIconsStillRender:
    """Turning replacement off for data keeps the status icons the output shows today."""

    def test_report_status_icons_render_as_emoji_glyphs(self) -> None:
        """The error icon is the glyph Rich draws for ``:cross_mark:``, not the token."""
        text = report_text({Path("SKILL.md"): [("FrontmatterValidator", issue_on_line(3))]})

        assert Emoji.replace(":cross_mark:") in text
        assert ":cross_mark:" not in text


class TestRecordingConsole:
    """The ``--record`` console keeps data literal for every renderable, not only reporter strings."""

    def test_make_recording_console_prints_emoji_code_literally(self) -> None:
        """A plain string printed on the recording console is not emoji-replaced."""
        buffer = StringIO()
        console = make_recording_console(file=buffer)

        console.print("SKILL.md:100: text")

        assert "SKILL.md:100: text" in plain(buffer.getvalue())
        assert "SKILL.md:100: text" in plain(console.export_text())


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    """Return an isolated working directory, HOME and PATH for the child process."""
    return Sandbox.create(tmp_path)


@pytest.fixture
def line_100_plugin(sandbox: Sandbox) -> Callable[[], Path]:
    """Build a plugin whose out-of-plugin link (LK004, an info issue) sits on line 100."""

    def build() -> Path:
        plugin = sandbox.case / "plugin"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text(
            '{"name":"demo","version":"1.0.0","description":"A demo plugin used for the reproduction."}\n',
            encoding="utf-8",
        )
        skill = plugin / LINE_100_PLUGIN_FILE
        skill.parent.mkdir(parents=True)
        head = ["---", "name: demo", "description: Use when reproducing the line-number emoji defect in output.", "---"]
        body = [*head, *["pad"] * (99 - len(head)), "See [Rules](../../../outside.md)"]
        skill.write_text("\n".join(body) + "\n", encoding="utf-8")
        return plugin

    return build


class TestRealExecutable:
    """The installed ``skilllint`` prints ``:100:`` on a coloured terminal and in a ``--record`` export."""

    @pytest.mark.parametrize("profile", ["force-color", "xterm256-truecolor"])
    def test_check_line_100_prints_the_number(
        self, sandbox: Sandbox, line_100_plugin: Callable[[], Path], profile: str
    ) -> None:
        """``check -v`` on a link at line 100 prints ``SKILL.md:100:`` where it used to print an emoji."""
        plugin = line_100_plugin()

        run = run_cli(["check", "-v", str(plugin)], sandbox, profile=profile)

        assert f"{LINE_100_PLUGIN_FILE}:100: Link" in plain(run.stdout.decode("utf-8"))

    def test_check_record_export_holds_the_number(self, sandbox: Sandbox, line_100_plugin: Callable[[], Path]) -> None:
        """The ``--record`` HTML export holds ``:100:`` too, since it records the same console."""
        plugin = line_100_plugin()
        export = sandbox.case / "out.html"

        run_cli(["check", "-v", "--record", str(export), str(plugin)], sandbox, profile="force-color")

        assert f"{LINE_100_PLUGIN_FILE}:100:" in export.read_text(encoding="utf-8")

    def test_check_ci_reporter_holds_the_number(self, sandbox: Sandbox, line_100_plugin: Callable[[], Path]) -> None:
        """The plain-text reporter is the reference behaviour the coloured one must match."""
        plugin = line_100_plugin()

        run = run_cli(["check", "-v", "--no-color", str(plugin)], sandbox)

        assert f"{LINE_100_PLUGIN_FILE}:100: Link" in run.stdout.decode("utf-8")


class TestErrorTextFromUserInput:
    """Text the user typed on the command line is echoed literally in an error."""

    def test_docs_latest_no_cache_prints_page_name_literally(
        self, cli_runner: CliRunner, mocker: MockerFixture
    ) -> None:
        """``docs latest`` echoes a page name holding ``:100:`` as typed."""
        mocker.patch("skilllint.cli_docs.find_latest", return_value=None)

        result = cli_runner.invoke(plugin_validator.app, ["docs", "latest", "page:100:name"])

        assert "page:100:name" in result.output

    def test_rule_unknown_id_prints_emoji_code_literally(self, cli_runner: CliRunner) -> None:
        """``rule`` echoes an unknown id holding ``:100:`` as typed."""
        result = cli_runner.invoke(plugin_validator.app, ["rule", "X:100:"])

        assert result.exit_code == 1
        assert "Unknown rule: X:100:" in result.output

    def test_rule_unknown_id_prints_markup_literally(self, cli_runner: CliRunner) -> None:
        """An unknown id that looks like a closing tag is printed, not raised as a markup error."""
        result = cli_runner.invoke(plugin_validator.app, ["rule", "[/bold]"])

        assert result.exit_code == 1
        assert "Unknown rule: [/bold]" in result.output


class TestPanelWidth:
    """A panel holding ``:name:`` data is measured the way it is printed."""

    def test_panel_border_fits_literal_emoji_code(self) -> None:
        """The border is as wide as the literal ``:100:`` line, so the text neither wraps nor spills."""
        buffer = StringIO()
        console = Console(file=buffer, width=200, soft_wrap=True, emoji=False)  # as the docs consoles are built

        print_panel(console, Panel("a :100: b :smile: c :warning: d"))

        lines = buffer.getvalue().splitlines()
        assert any("a :100: b :smile: c :warning: d" in line for line in lines)
        assert len({cell_len(line) for line in lines}) == 1
