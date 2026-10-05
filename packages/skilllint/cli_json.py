"""The CLI side of ``--json``: the option every command shares and the way a command ends under it.

``--json`` is a per-command option. It is declared once here as :data:`JsonOption`, so each command
that offers it spells it, and documents it, the same way. :func:`emit_and_exit` is how a command
finishes under ``--json``: one response line on stdout through
:func:`skilllint.responses.emit_response`, then the exit status. The module renders nothing, so
no Rich output can reach either stream on this path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, NoReturn

import typer
from typer._click.exceptions import MissingParameter

from skilllint.responses import emit_response

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["JsonOption", "emit_and_exit", "fail_missing_argument"]

JsonOption = Annotated[
    bool, typer.Option("--json", help="Print one compact JSON line on stdout instead of the text output.")
]
"""``--json`` as a command parameter; name the Python parameter ``json_output`` so it does not shadow ``json``."""


def emit_and_exit(response: BaseModel, *, code: int = 0) -> NoReturn:
    """Print *response* as the command's one JSON line and exit.

    Args:
        response: The response model to print.
        code: The exit status: 0 for a pass, 1 for a failure that is itself a result.

    Raises:
        typer.Exit: Always, with *code*.
    """
    emit_response(response)
    raise typer.Exit(code) from None


def fail_missing_argument(ctx: typer.Context, name: str) -> NoReturn:
    """Fail with the usage error Click itself raises for a missing argument.

    Under ``--json`` a command that is given no paths must not print its help on stdout, so it
    reports the same error Click reports for a required argument: a plain message on stderr,
    exit status 2, and an empty stdout.

    Args:
        ctx: The context of the running command.
        name: The Python name of the missing argument, as declared on the command.

    Raises:
        MissingParameter: Always; Typer turns it into the usage error and exit status 2.
    """
    param = next(candidate for candidate in ctx.command.params if candidate.name == name)
    raise MissingParameter(ctx=ctx, param=param)
