"""``--json`` carries a path that is not valid UTF-8 as a JSON escape, losing nothing.

A POSIX path may hold bytes that are not UTF-8. Python reads such an argument with
``surrogateescape``, so the string holds a lone surrogate, and the default output shows it as ``?``
because its stdout replaces what it cannot encode. ``--json`` must neither crash (a serialisation
traceback with exit 1 and an empty stdout is indistinguishable from "validation failed") nor lose
the byte: two different bad paths would collide as ``?``. The lone surrogate is written as the JSON
escape ``\\udcff``, which is valid JSON, and a Python consumer recovers the original bytes with
``os.fsencode(json.loads(line))``. Ordinary non-ASCII text stays readable and unescaped.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import TYPE_CHECKING, Final, TypeVar

import pytest
from cli_probe import CliRun, Sandbox
from default_output_cases import Case, workspace
from json_probe_support import (
    CheckResponse,
    RuleUnknownResponse,
    SectionNotFoundResponse,
    SectionsResponse,
    TokensResponse,
    VerifyResponse,
    run_probe,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from default_output_cases import Endpoints

BAD_NAME: Final = os.fsdecode(b"sk\xff")
"""A name that is not UTF-8: the string holds ``\\udcff`` and the file system holds the byte ``0xff``."""

BAD_BYTES: Final = b"sk\xff"
ESCAPED_NAME: Final = "sk\\udcff"
"""How ``BAD_NAME`` appears in the JSON text: the escape, not the character."""

ModelT = TypeVar("ModelT", bound=BaseModel)


def load(model: type[ModelT], run: CliRun) -> ModelT:
    """Read a run's stdout as one line of valid JSON and validate it as *model*.

    The line is read with ``json``: pydantic's own JSON parser rejects a lone-surrogate escape, which is
    exactly what a Python consumer of this output has to cope with.

    Returns:
        The validated response.
    """
    assert run.stdout.endswith(b"\n"), run.stderr.decode(errors="replace")
    assert run.stdout.count(b"\n") == 1, "stdout is more than one line"
    assert b"\xff" not in run.stdout, "the raw byte leaked into stdout"
    return model.model_validate(json.loads(run.stdout))


def original_bytes(shown: str, suffix: bytes = b"") -> bytes:
    """Return what ``os.fsencode`` recovers from a value the consumer read out of the JSON."""
    return os.fsencode(shown) + suffix


def bad_workspace(sandbox: Sandbox, endpoints: Endpoints) -> None:
    """Add ``BAD_NAME/`` (a fixable skill) beside the shared tree."""
    workspace(sandbox, endpoints)
    shutil.copytree(sandbox.case / "fixme", sandbox.case / BAD_NAME)


def case(*args: str, setup: Callable[[Sandbox, Endpoints], None] = bad_workspace) -> Case:
    """Build an unnamed probe case."""
    return Case("probe", args, setup=setup, docs=args[0] == "docs")


def test_check_lists_the_path_as_an_escape_that_round_trips(tmp_path: Path) -> None:
    """``files[].path`` is the escaped name, and ``os.fsencode`` gives the file system bytes back."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--verbose", "--json"))

    response = load(CheckResponse, run)
    assert f"{ESCAPED_NAME}/SKILL.md".encode() in run.stdout
    assert [os.fsencode(file.path) for file in response.files] == [BAD_BYTES + b"/SKILL.md"]
    assert run.returncode == 1


def test_fix_reports_the_fixed_path_the_same_way(tmp_path: Path) -> None:
    """``fixes[].path`` round-trips, and the fix itself still happens."""
    sandbox, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--fix", "--json"))

    response = load(CheckResponse, run)
    assert response.fixes
    assert {os.fsencode(fix.path) for fix in response.fixes} == {BAD_BYTES + b"/SKILL.md"}
    assert (sandbox.case / BAD_NAME / "SKILL.md").read_bytes() != (sandbox.case / "invalid_skill.md").read_bytes()


def test_tokens_only_lists_the_path_the_same_way(tmp_path: Path) -> None:
    """``tokens[].path`` round-trips."""
    _, run = run_probe(tmp_path, case("check", f"{BAD_NAME}/SKILL.md", "--tokens-only", "--json"))

    response = load(TokensResponse, run)
    assert [os.fsencode(entry.path) for entry in response.tokens] == [BAD_BYTES + b"/SKILL.md"]
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
    """A file argument that is not UTF-8 appears in ``file`` as the escape and round-trips."""
    _, run = run_probe(tmp_path, case(*args, "--json"))

    response = load(model, run)
    assert f"{ESCAPED_NAME}.md".encode() in run.stdout
    assert os.fsencode(response.file) == BAD_BYTES + b".md"
    assert response.file_exists is False


def test_docs_section_query_and_rule_id_are_echoed_the_same_way(tmp_path: Path) -> None:
    """User strings echoed back (a heading query, a rule id) round-trip too."""
    _, section = run_probe(tmp_path, case("docs", "section", "absent.md", BAD_NAME, "--json"), root="section")
    _, rule = run_probe(tmp_path, case("rule", BAD_NAME, "--json"), root="rule")

    assert os.fsencode(load(SectionNotFoundResponse, section).query) == BAD_BYTES
    unknown = load(RuleUnknownResponse, rule)
    assert os.fsencode(unknown.rule_id) == BAD_BYTES
    assert rule.returncode == 1


def test_two_different_bad_paths_stay_distinct(tmp_path: Path) -> None:
    """The replacement character made ``sk\\xff`` and ``sk\\xfe`` collide; the escape keeps them apart."""
    other = os.fsdecode(b"sk\xfe")
    _, first = run_probe(tmp_path, case("rule", BAD_NAME, "--json"), root="first")
    _, second = run_probe(tmp_path, case("rule", other, "--json"), root="second")

    assert load(RuleUnknownResponse, first).rule_id != load(RuleUnknownResponse, second).rule_id


def test_ordinary_non_ascii_beside_a_bad_byte_stays_readable(tmp_path: Path) -> None:
    """Only the lone surrogate is escaped; ``é`` and a non-BMP character are written as UTF-8."""
    mixed = f"é{BAD_NAME}\U0001d11e"
    _, run = run_probe(tmp_path, case("rule", mixed, "--json"))

    unknown = load(RuleUnknownResponse, run)
    assert "é".encode() in run.stdout
    assert "\U0001d11e".encode() in run.stdout
    assert f"{ESCAPED_NAME}".encode() in run.stdout
    assert unknown.rule_id == mixed
