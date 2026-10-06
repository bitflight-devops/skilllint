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


def test_check_preserves_the_machine_path_while_text_uses_display_replacement(tmp_path: Path) -> None:
    """The JSON path remains exact even though the text reporter must display a replacement."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--verbose", "--json"))
    shown = default_listed_path(tmp_path, f"{BAD_NAME}/SKILL.md", "--verbose")

    response = parse(CheckResponse, run)
    assert shown == f"{SHOWN_NAME}/SKILL.md"
    assert [file.path for file in response.files] == [f"{BAD_NAME}/SKILL.md"]
    assert run.returncode in {0, 1}


def test_fix_preserves_the_machine_path_identity(tmp_path: Path) -> None:
    """``fixes[].path`` carries the replaced character, and the fix itself still happens."""
    sandbox, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--fix", "--json"))

    response = parse(CheckResponse, run)
    assert response.fixes
    assert {fix.path for fix in response.fixes} == {f"{BAD_NAME}/SKILL.md"}
    assert (sandbox.case / BAD_NAME / "SKILL.md").read_bytes() != (sandbox.case / "invalid_skill.md").read_bytes()


def test_tokens_only_preserves_the_machine_path_identity(tmp_path: Path) -> None:
    """``tokens[].path`` carries the replaced character."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--tokens-only", "--json"))

    response = parse(TokensResponse, run)
    assert [entry.path for entry in response.tokens] == [f"{BAD_NAME}/SKILL.md"]
    assert run.returncode == 0


@pytest.mark.parametrize(
    ("args", "model"),
    [
        pytest.param(("docs", "sections", f"{BAD_NAME}.md"), SectionsResponse, id="sections"),
        pytest.param(("docs", "section", f"{BAD_NAME}.md", "Usage"), SectionNotFoundResponse, id="section"),
        pytest.param(("docs", "verify", f"{BAD_NAME}.md"), VerifyResponse, id="verify"),
    ],
)
def test_docs_file_argument_preserves_machine_path_identity(
    args: tuple[str, ...], model: type[SectionsResponse | SectionNotFoundResponse | VerifyResponse], tmp_path: Path
) -> None:
    """A file argument that is not UTF-8 appears in ``file`` with the replaced character."""
    _, run = run_probe(tmp_path, case(*args, "--json"))

    response = parse(model, run)
    assert response.file == f"{BAD_NAME}.md"
    assert response.file_exists is False


def test_docs_query_and_rule_id_preserve_machine_identity(tmp_path: Path) -> None:
    """User strings echoed back (a heading query, a rule id) get the same treatment."""
    _, section = run_probe(tmp_path, case("docs", "section", "absent.md", BAD_NAME, "--json"), root="section")
    _, rule = run_probe(tmp_path, case("rule", BAD_NAME, "--json"), root="rule")

    assert parse(SectionNotFoundResponse, section).query == BAD_NAME
    unknown = parse(RuleUnknownResponse, rule)
    assert unknown.rule_id == BAD_NAME
    assert rule.returncode == 1

def test_distinct_non_utf8_paths_do_not_collapse_after_json_round_trip(tmp_path: Path) -> None:
    """Different undecodable bytes remain different machine-readable path identities."""
    other_name = os.fsdecode(b"sk\xfe")

    def two_bad_workspaces(sandbox: Sandbox, endpoints: Endpoints) -> None:
        workspace(sandbox, endpoints)
        shutil.copytree(sandbox.case / "fixme", sandbox.case / BAD_NAME)
        shutil.copytree(sandbox.case / "fixme", sandbox.case / other_name)

    _, first = run_probe(
        tmp_path,
        case("check", f"{BAD_NAME}/SKILL.md", "--show-progress", "--json", setup=two_bad_workspaces),
        root="first",
    )
    _, second = run_probe(
        tmp_path,
        case("check", f"{other_name}/SKILL.md", "--show-progress", "--json", setup=two_bad_workspaces),
        root="second",
    )

    first_path = parse(CheckResponse, first).files[0].path
    second_path = parse(CheckResponse, second).files[0].path
    assert first_path == f"{BAD_NAME}/SKILL.md"
    assert second_path == f"{other_name}/SKILL.md"
    assert first_path != second_path
