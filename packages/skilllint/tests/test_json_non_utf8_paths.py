"""``--json`` carries a path that is not valid UTF-8 the way the default output shows it.

A POSIX path may hold bytes that are not UTF-8. Python reads such an argument with
``surrogateescape``, so the string holds a lone surrogate. The default output writes it through a
stdout that replaces what it cannot encode, so the byte shows as ``?`` and the command exits
normally. ``--json`` must not turn that into a serialisation traceback with exit 1 and an empty
stdout, which an agent cannot tell from "validation failed": it carries the same ``?``.
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, Final

import pytest
from cli_probe import Sandbox
from default_output_cases import Case, workspace
from json_probe_support import (
    CheckResponse,
    RuleUnknownResponse,
    SectionNotFoundResponse,
    SectionsResponse,
    TokensResponse,
    VerifyResponse,
    parse,
    run_probe,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from default_output_cases import Endpoints

BAD_NAME: Final = os.fsdecode(b"sk\xff")
"""A name that is not UTF-8: the string holds ``\\udcff`` and the file system holds the byte ``0xff``."""

SHOWN_NAME: Final = "sk?"
"""How the default output shows ``BAD_NAME``: stdout replaces what it cannot encode with ``?``."""


def bad_workspace(sandbox: Sandbox, endpoints: Endpoints) -> None:
    """Add ``BAD_NAME/`` (a fixable skill) beside the shared tree."""
    workspace(sandbox, endpoints)
    shutil.copytree(sandbox.case / "fixme", sandbox.case / BAD_NAME)


def case(*args: str, setup: Callable[[Sandbox, Endpoints], None] = bad_workspace) -> Case:
    """Build an unnamed probe case."""
    return Case("probe", args, setup=setup, docs=args[0] == "docs")


def default_listed_path(tmp_path: Path, *args: str) -> str:
    """Return the file path the default text output prints first for *args*."""
    _, run = run_probe(tmp_path, case("check", "--no-color", *args), root="default")
    return next(line for line in run.stdout.decode().splitlines() if line.strip())


def test_check_lists_the_path_as_the_default_output_shows_it(tmp_path: Path) -> None:
    """The file path in ``files`` is the one the default output prints, ``?`` included."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--verbose", "--json"))
    shown = default_listed_path(tmp_path, f"{BAD_NAME}/SKILL.md", "--verbose")

    response = parse(CheckResponse, run)
    assert shown == f"{SHOWN_NAME}/SKILL.md"
    assert [file.path for file in response.files] == [shown]
    assert run.returncode in {0, 1}


def test_fix_reports_the_fixed_path_the_same_way(tmp_path: Path) -> None:
    """``fixes[].path`` carries the replaced character, and the fix itself still happens."""
    sandbox, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--fix", "--json"))

    response = parse(CheckResponse, run)
    assert response.fixes
    assert {fix.path for fix in response.fixes} == {f"{SHOWN_NAME}/SKILL.md"}
    assert (sandbox.case / BAD_NAME / "SKILL.md").read_bytes() != (sandbox.case / "invalid_skill.md").read_bytes()


def test_tokens_only_lists_the_path_the_same_way(tmp_path: Path) -> None:
    """``tokens[].path`` carries the replaced character."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--tokens-only", "--json"))

    response = parse(TokensResponse, run)
    assert [entry.path for entry in response.tokens] == [f"{SHOWN_NAME}/SKILL.md"]
    assert run.returncode == 0


@pytest.mark.parametrize(
    ("args", "model"),
    [
        pytest.param(("docs", "sections", f"{BAD_NAME}.md"), SectionsResponse, id="sections"),
        pytest.param(("docs", "section", f"{BAD_NAME}.md", "Usage"), SectionNotFoundResponse, id="section"),
        pytest.param(("docs", "verify", f"{BAD_NAME}.md"), VerifyResponse, id="verify"),
    ],
)
def test_docs_file_argument_is_echoed_the_same_way(
    args: tuple[str, ...], model: type[SectionsResponse | SectionNotFoundResponse | VerifyResponse], tmp_path: Path
) -> None:
    """A file argument that is not UTF-8 appears in ``file`` with the replaced character."""
    _, run = run_probe(tmp_path, case(*args, "--json"))

    response = parse(model, run)
    assert response.file == f"{SHOWN_NAME}.md"
    assert response.file_exists is False


def test_docs_section_query_and_rule_id_are_echoed_the_same_way(tmp_path: Path) -> None:
    """User strings echoed back (a heading query, a rule id) get the same treatment."""
    _, section = run_probe(tmp_path, case("docs", "section", "absent.md", BAD_NAME, "--json"), root="section")
    _, rule = run_probe(tmp_path, case("rule", BAD_NAME, "--json"), root="rule")

    assert parse(SectionNotFoundResponse, section).query == SHOWN_NAME
    unknown = parse(RuleUnknownResponse, rule)
    assert unknown.rule_id == SHOWN_NAME
    assert rule.returncode == 1
