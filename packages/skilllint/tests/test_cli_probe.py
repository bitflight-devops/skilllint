"""Tests for the subprocess probe harness in ``cli_probe``.

The baseline and ``--json`` probe suites trust this harness: if its pty mode
rewrote newlines, or its stderr filter ate real output, a green baseline would
prove nothing. These tests pin the harness behaviours those suites rely on.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from cli_probe import (
    ENV_PROFILES,
    NARROW_COLUMNS,
    WIDE_COLUMNS,
    Sandbox,
    build_env,
    help_delta,
    normalise,
    run_cli,
    run_on_pty,
    strip_shallow_clone_warning,
)

if TYPE_CHECKING:
    from pathlib import Path

_WARNING = (
    b'/venv/lib/python3.11/site-packages/vcs_versioning/_backends/_git.py:367: UserWarning: "/repo" is shallow and may cause errors\n'
    b"  pre_parse(wd)\n"
)


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox.create(tmp_path)


class TestShallowCloneWarningFilter:
    def test_removes_both_lines_and_nothing_else(self) -> None:
        assert strip_shallow_clone_warning(_WARNING + b"real stderr\n") == b"real stderr\n"

    def test_removes_the_warning_wherever_it_sits(self) -> None:
        assert strip_shallow_clone_warning(b"before\n" + _WARNING + b"after\n") == b"before\nafter\n"

    def test_keeps_a_warning_with_different_wording(self) -> None:
        other = b'x.py:1: UserWarning: "/repo" has a different problem\n  pre_parse(wd)\n'

        assert strip_shallow_clone_warning(other) == other

    def test_keeps_the_first_line_when_the_second_is_missing(self) -> None:
        first_line_only = _WARNING.splitlines(keepends=True)[0]

        assert strip_shallow_clone_warning(first_line_only) == first_line_only

    def test_does_not_make_empty_stderr_the_expectation(self) -> None:
        """Stderr other than the warning survives, so a golden can record it."""
        assert strip_shallow_clone_warning(b"Warning: config ignored\n" + _WARNING) == b"Warning: config ignored\n"


class TestPinnedEnvironment:
    def test_nothing_is_inherited_from_the_test_process(
        self, sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name in ("CLAUDECODE", "NO_COLOR", "FORCE_COLOR", "TERM", "PYTHONUNBUFFERED"):
            monkeypatch.setenv(name, "1")

        env = build_env(sandbox)

        assert set(env) == {"HOME", "PATH", "COLUMNS"}

    def test_each_profile_adds_exactly_its_own_variables(self, sandbox: Sandbox) -> None:
        for profile, variables in ENV_PROFILES.items():
            assert set(build_env(sandbox, profile=profile)) == {"HOME", "PATH", "COLUMNS", *variables}

    def test_pty_runs_leave_columns_unset_so_the_window_size_decides(self, sandbox: Sandbox) -> None:
        assert "COLUMNS" not in build_env(sandbox, columns=None)

    def test_path_holds_only_git_so_no_claude_binary_is_found(self, sandbox: Sandbox) -> None:
        assert [entry.name for entry in sandbox.bin.iterdir()] == ["git"]


class TestRunCli:
    def test_pty_and_merge_cannot_be_combined(self, sandbox: Sandbox) -> None:
        with pytest.raises(ValueError, match="pipe-only"):
            run_cli(["--version"], sandbox, tty_stdout=True, merge_stderr=True)

    def test_pty_capture_is_byte_identical_to_a_pipe_for_plain_output(self, sandbox: Sandbox) -> None:
        """Raw mode keeps the line discipline from turning ``\\n`` into ``\\r\\n``."""
        piped = run_cli(["--version"], sandbox)
        on_pty = run_cli(["--version"], sandbox, tty_stdout=True)

        assert on_pty.stdout == piped.stdout
        assert b"\r" not in on_pty.stdout

    def test_pty_window_size_is_what_the_child_reads(self, sandbox: Sandbox) -> None:
        """A child that asks its terminal for its size gets the requested columns."""
        probe = [sys.executable, "-c", "import os, sys; print(sys.stdout.isatty(), os.get_terminal_size().columns)"]
        env = build_env(sandbox, columns=None)

        _, narrow, _ = run_on_pty(probe, env=env, cwd=sandbox.case, columns=NARROW_COLUMNS)
        _, wide, _ = run_on_pty(probe, env=env, cwd=sandbox.case, columns=WIDE_COLUMNS)

        assert narrow == f"True {NARROW_COLUMNS}\n".encode()
        assert wide == f"True {WIDE_COLUMNS}\n".encode()

    def test_stderr_stays_separate_from_a_pty_stdout(self, sandbox: Sandbox) -> None:
        run = run_cli(["check", "nope.md"], sandbox, tty_stdout=True)

        assert run.stderr.startswith(b"Path does not exist: nope.md")
        assert b"Path does not exist" not in run.stdout

    def test_merged_capture_keeps_stderr_before_the_stdout_that_followed_it(self, sandbox: Sandbox) -> None:
        separate = run_cli(["check", "nope.md"], sandbox)
        merged = run_cli(["check", "nope.md"], sandbox, merge_stderr=True)

        assert separate.stderr
        assert separate.stdout
        assert merged.stdout == separate.stderr + separate.stdout
        assert merged.returncode == separate.returncode == 2

    def test_runs_in_the_sandbox_working_directory(self, sandbox: Sandbox) -> None:
        (sandbox.case / "SKILL.md").write_text("---\nname: x\ndescription: Use when testing.\n---\n\nBody.\n")

        run = run_cli(["check", "SKILL.md", "--no-color"], sandbox)

        assert run.stdout.startswith(b"\nSKILL.md\n")


class TestNormalise:
    def test_replaces_sandbox_locations_in_resolved_and_given_spelling(self, sandbox: Sandbox) -> None:
        text = f"{sandbox.case} {sandbox.case.resolve()} {sandbox.home} {sandbox.bin}"

        assert normalise(text, sandbox, ()) == "<CASE> <CASE> <HOME> <BIN>"

    @pytest.mark.parametrize(
        "version", ["1.20.14", "1.20.14.dev7+g2edc05d6f", "1.20.14.dev7+g2edc05d6f.d20261005"], ids=str
    )
    def test_version_normaliser_covers_release_dev_and_dirty_tree_forms(self, sandbox: Sandbox, version: str) -> None:
        assert normalise(f"skilllint {version}\n", sandbox, ("version",)) == "skilllint <VERSION>\n"

    def test_traceback_normaliser_keeps_the_exception_and_drops_frames(self, sandbox: Sandbox) -> None:
        text = (
            "Traceback (most recent call last):\n"
            '  File "/a/b.py", line 10, in main\n'
            "    run()\n"
            "    ^^^^^\n"
            '  File "/a/c.py", line 3, in run\n'
            "    raise ValueError('boom')\n"
            "ValueError: boom\n"
        )

        assert normalise(text, sandbox, ("traceback",)) == (
            "Traceback (most recent call last):\n  <frames elided>\nValueError: boom\n"
        )

    def test_port_and_timestamp_normalisers_keep_the_width_of_what_they_replace(self, sandbox: Sandbox) -> None:
        text = "http://127.0.0.1:41234/x.md page-2026-10-05-1432.md"

        assert normalise(text, sandbox, ("port", "timestamp")) == "http://127.0.0.1:00000/x.md page-0000-00-00-0000.md"

    def test_temp_name_normaliser_replaces_the_random_stem(self, sandbox: Sandbox) -> None:
        assert normalise("dir/tmpnrhve02u.svg", sandbox, ("temp-name",)) == "dir/tmp<RAND>.svg"


_OLD_HELP = "Options:\n  --check  Validate only\n  --help   Show this message and exit.\n"
_OPTION = "  --json   Emit JSON\n"


class TestHelpDelta:
    def test_identical_help_has_no_delta(self) -> None:
        assert help_delta(_OLD_HELP, _OLD_HELP) == []

    def test_one_inserted_json_option_line_is_the_whole_delta(self) -> None:
        new = _OLD_HELP.replace("  --help", _OPTION + "  --help")

        assert help_delta(_OLD_HELP, new) == [_OPTION]

    def test_a_wrapped_json_option_entry_is_one_block(self) -> None:
        wrapped = "  --json   Emit\n           JSON\n"
        new = _OLD_HELP.replace("  --help", wrapped + "  --help")

        assert help_delta(_OLD_HELP, new) == wrapped.splitlines(keepends=True)

    def test_a_removed_line_is_rejected(self) -> None:
        new = _OLD_HELP.replace("  --check  Validate only\n", "").replace("  --help", _OPTION + "  --help")

        with pytest.raises(ValueError, match="only gain lines"):
            help_delta(_OLD_HELP, new)

    def test_a_changed_line_is_rejected(self) -> None:
        new = _OLD_HELP.replace("Validate only", "Validate").replace("  --help", _OPTION + "  --help")

        with pytest.raises(ValueError, match="only gain lines"):
            help_delta(_OLD_HELP, new)

    def test_an_inserted_line_that_is_not_the_json_option_is_rejected(self) -> None:
        new = _OLD_HELP.replace("  --help", "  --other  Something\n  --help")

        with pytest.raises(ValueError, match="does not start with the --json option"):
            help_delta(_OLD_HELP, new)

    def test_an_extra_unrelated_line_after_the_json_option_is_rejected(self) -> None:
        new = _OLD_HELP.replace("  --help", _OPTION + "  --other  Something\n  --help")

        with pytest.raises(ValueError, match="more than the --json option entry"):
            help_delta(_OLD_HELP, new)

    def test_two_separate_insertions_are_rejected(self) -> None:
        new = "extra\n" + _OLD_HELP.replace("  --help", _OPTION + "  --help")

        with pytest.raises(ValueError, match="only gain lines"):
            help_delta(_OLD_HELP, new)
