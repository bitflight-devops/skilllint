"""Select GitHub diagnostic safety before the CLI parser or exceptions render.

Raw arguments and context keywords remain inputs to Typer's existing parser.
Only the stderr presentation of an explicitly requested GitHub check changes.
"""

from __future__ import annotations

import sys
import traceback
from contextlib import nullcontext
from typing import TYPE_CHECKING

from typer.core import TyperOption

from skilllint.cli_help import CompleteHelpGroup
from skilllint.reporting_github import github_diagnostics

if TYPE_CHECKING:
    from collections.abc import Sequence


def _after_option(args: Sequence[str], index: int, options: dict[str, TyperOption]) -> int:
    """Skip the values consumed by this option, using the actual CLI schema.

    Returns:
        Index of the next unconsumed token, including incomplete invocations.
    """
    name, separator, _value = args[index].partition("=")
    option = options.get(name)
    if option is None or option.is_flag:
        return index + 1
    return index + 1 + max(0, option.nargs - bool(separator))


class GitHubDiagnosticGroup(CompleteHelpGroup):
    """Protect parsing and exception rendering at every public CLI entrypoint."""

    def _requests_github(self, args: Sequence[str]) -> bool:
        """Recognize a requested format without reimplementing CLI validation.

        Returns:
            Whether the check command's last explicit format is GitHub.
        """
        root_options = {
            name: option for option in self.params if isinstance(option, TyperOption) for name in option.opts
        }
        index = 0
        while index < len(args) and args[index].startswith("-"):
            if args[index] == "--":
                index += 1
                break
            index = _after_option(args, index, root_options)
        if index >= len(args) or args[index] != "check":
            return False
        command = self.commands.get("check")
        if command is None:
            return False
        options = {name: option for option in command.params if isinstance(option, TyperOption) for name in option.opts}
        selected = None
        index += 1
        while index < len(args):
            argument = args[index]
            if argument == "--":
                break
            name, separator, value = argument.partition("=")
            if name == "--output-format":
                selected = value if separator else args[index + 1] if index + 1 < len(args) else None
            index = _after_option(args, index, options)
        return selected == "github"

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: object,
    ) -> object:
        """Delegate parsing unchanged and keep terminal tracebacks in the guard.

        Returns:
            Typer's original non-standalone result.

        Raises:
            SystemExit: Original CLI exit status, or 1 for an uncaught error.
            Exception: Original exception in non-GitHub or non-standalone mode.
        """
        github = self._requests_github(sys.argv[1:] if args is None else args)
        with github_diagnostics() if github else nullcontext():
            try:
                return super().main(
                    args=args,
                    prog_name=prog_name,
                    complete_var=complete_var,
                    standalone_mode=standalone_mode,
                    windows_expand_args=windows_expand_args,
                    **extra,
                )
            except Exception:
                if not github or not standalone_mode:
                    raise
                traceback.print_exc()
                raise SystemExit(1) from None
