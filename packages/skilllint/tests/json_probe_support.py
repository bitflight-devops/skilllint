"""Expected ``--json`` response shapes and assertion helpers for the contract probes.

The models are written from the migration brief and its spec, not imported from
the implementation. They are strict (``extra="forbid"``, ``strict=True``) so a
missing, renamed, mistyped or extra key fails validation, and they are
deliberately separate from the response models the migration adds: a test that
imported the implementation's own models could not disagree with it.

Field order inside a model is irrelevant here; compactness is checked on the raw
bytes by :func:`assert_one_compact_line`.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Final, Literal, TypeVar

from cli_probe import CliRun, Sandbox
from default_output_cases import DEFAULT_VARIANT, Case, Variant, case_endpoints, run_case
from pydantic import BaseModel, ConfigDict, JsonValue, TypeAdapter

if TYPE_CHECKING:
    from pathlib import Path

# --- recorded RED reason ---------------------------------------------------------

NO_SUCH_OPTION: Final = b"No such option: --json"
"""What the CLI prints today for ``--json``: the one reason every probe is red."""

_JSON_DOCUMENT: Final = TypeAdapter(JsonValue)
_BOX_DRAWING: Final = re.compile(r"[─-╿]")

# --- expected response shapes ------------------------------------------------------


class Strict(BaseModel):
    """Base for expected shapes: frozen, strict, no unknown keys."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


Status = Literal["passed", "failed"]


class IssueShape(Strict):
    """``ValidationIssue`` as the brief says it is emitted: all seven keys, always."""

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: str
    line: int | None
    suggestion: str | None
    docs_url: str | None


class ValidatorShape(Strict):
    """One validator entry inside a listed file."""

    name: str
    status: Status
    issues: list[IssueShape]


class CheckedFileShape(Strict):
    """One entry of ``files``."""

    path: str
    status: Status
    validators: list[ValidatorShape]


class SummaryShape(Strict):
    """``summary``; ``passed_with_warnings`` is what ``_compute_summary`` calls ``warnings``."""

    total_files: int
    passed: int
    failed: int
    passed_with_warnings: int


class OmittedShape(Strict):
    """``omitted``: what the listing left out, and the flags that bring it back."""

    passed_files: int
    passed_validators: int
    info_issues: int
    retrieve_with: list[str]


class AppliedFixShape(Strict):
    """One entry of ``fixes`` (the existing ``AppliedFix`` dataclass)."""

    path: str
    validator: str
    codes: list[str]
    description: str


class RecordedResponse(Strict):
    """Base of the responses of commands that accept ``--record``."""

    record_path: str | None


class FileResponse(Strict):
    """Base of the responses that carry the JSON-only ``file_exists``."""

    file_exists: bool


class CheckResponse(RecordedResponse):
    """``skilllint check --json``."""

    command: Literal["check"]
    status: Status
    summary: SummaryShape
    files: list[CheckedFileShape]
    fixes: list[AppliedFixShape]
    omitted: OmittedShape


class TokenCountShape(Strict):
    """One entry of ``tokens``."""

    path: str
    tokens: int


class TokensResponse(RecordedResponse):
    """``skilllint check --tokens-only --json``."""

    command: Literal["check --tokens-only"]
    tokens: list[TokenCountShape]


class RuleRowShape(Strict):
    """One row of the rules table."""

    id: str
    severity: str
    category: str
    fixable: bool
    summary: str


class RulesResponse(RecordedResponse):
    """``skilllint rules --json``."""

    command: Literal["rules"]
    rules: list[RuleRowShape]
    summary_note: str


class RuleFoundResponse(RecordedResponse):
    """``skilllint rule <known id> --json``."""

    command: Literal["rule"]
    status: Literal["found"]
    id: str
    severity: str
    category: str
    platforms: list[str]
    documentation: str


class RuleUnknownResponse(Strict):
    """``skilllint rule <unknown id> --json``; ``record_path`` is always null."""

    command: Literal["rule"]
    status: Literal["unknown"]
    rule_id: str
    list_command: Literal["skilllint rules"]
    record_path: None


class VersionResponse(Strict):
    """``skilllint --version --json``."""

    command: Literal["version"]
    name: Literal["skilllint"]
    version: str


CacheOutcome = Literal["new", "fresh", "refreshed", "unchanged", "stale"]
"""The ``CacheStatus`` values of ``skilllint.vendor_cache``."""


class FetchResponse(Strict):
    """``skilllint docs fetch --json`` when a file was produced."""

    command: Literal["docs fetch"]
    status: CacheOutcome
    path: str
    page_name: str
    url: str


class FetchNoCacheResponse(Strict):
    """``skilllint docs fetch --json`` when no cache exists and the network failed."""

    command: Literal["docs fetch"]
    status: Literal["no_cache"]
    url: str
    reason: str


class AuthorityResultShape(Strict):
    """One URL's outcome inside ``docs fetch-authorities``."""

    url: str
    status: CacheOutcome | Literal["failed"]
    path: str | None
    page_name: str | None
    reason: str | None


class AuthoritiesResponse(Strict):
    """``skilllint docs fetch-authorities --json``."""

    command: Literal["docs fetch-authorities"]
    status: Literal["ok", "failed"]
    results: list[AuthorityResultShape]


class LatestFoundResponse(Strict):
    """``skilllint docs latest --json`` with a match."""

    command: Literal["docs latest"]
    status: Literal["found"]
    page_name: str
    path: str


class LatestNotFoundResponse(Strict):
    """``skilllint docs latest --json`` without a match."""

    command: Literal["docs latest"]
    status: Literal["not_found"]
    page_name: str


class SectionShape(Strict):
    """One entry of ``docs sections``; the preamble is ``heading: ""``, ``level: 0``."""

    level: int
    heading: str
    line_start: int
    line_end: int


class SectionsResponse(FileResponse):
    """``skilllint docs sections --json``, with the JSON-only ``file_exists``."""

    command: Literal["docs sections"]
    file: str
    sections: list[SectionShape]


class SectionFoundResponse(FileResponse):
    """``skilllint docs section --json`` with a match."""

    command: Literal["docs section"]
    status: Literal["found"]
    file: str
    query: str
    heading: str
    level: int
    line_start: int
    line_end: int
    text: str


class SectionNotFoundResponse(FileResponse):
    """``skilllint docs section --json`` without a match."""

    command: Literal["docs section"]
    status: Literal["not_found"]
    file: str
    query: str


class VerifyResponse(FileResponse):
    """``skilllint docs verify --json``, with the JSON-only ``file_exists``."""

    command: Literal["docs verify"]
    status: Literal["intact", "modified", "unverifiable"]
    file: str
    computed_sha256: str
    computed_bytes: int
    expected_sha256: str | None
    expected_bytes: int | None


# --- running and asserting ------------------------------------------------------------


def run_probe(
    tmp_path: Path, case: Case, *, root: str = "run", variant: Variant = DEFAULT_VARIANT, merge: bool = False
) -> tuple[Sandbox, CliRun]:
    """Run *case* in a fresh sandbox below ``tmp_path / root``.

    Returns:
        The sandbox, which holds any file the command wrote, and the captured run.
    """
    with case_endpoints(case) as endpoints:
        return run_case(case, variant, tmp_path / root, endpoints, merge=merge)


def assert_flag_recognised(run: CliRun) -> None:
    """Fail with the recorded RED reason when the CLI rejected ``--json``."""
    assert NO_SUCH_OPTION not in run.stderr, f"CLI rejected the flag: {run.stderr.decode(errors='replace').strip()!r}"


def assert_plain(run: CliRun) -> None:
    """Assert that neither stream carries an ANSI escape or a box-drawing character."""
    for name, data in (("stdout", run.stdout), ("stderr", run.stderr)):
        assert b"\x1b" not in data, f"{name} holds an ANSI escape"
        assert not _BOX_DRAWING.search(data.decode("utf-8", errors="replace")), f"{name} holds box-drawing characters"


def assert_one_compact_line(stdout: bytes) -> None:
    """Assert that *stdout* is one JSON document, compact, ending in a single newline."""
    assert stdout.endswith(b"\n"), "stdout does not end in a newline"
    assert stdout.count(b"\n") == 1, "stdout is more than one line"
    document = _JSON_DOCUMENT.validate_json(stdout)
    compact = json.dumps(document, separators=(",", ":"), ensure_ascii=True) + "\n"
    assert stdout.decode("utf-8") == compact, "stdout is valid JSON but not compact"


def assert_plain_usage_error(run: CliRun) -> None:
    """Assert exit 2, an empty stdout and a plain, traceback-free message on stderr.

    Holds today for a rejected ``--json`` as well, so it is the check for guards
    that must stay green; probes that need the flag use :func:`assert_usage_error`.
    """
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr.strip(), "a usage error must say what is wrong on stderr"
    assert b"Traceback" not in run.stderr
    assert b"\x1b" not in run.stderr


def assert_usage_error(run: CliRun) -> None:
    """Assert :func:`assert_plain_usage_error` for a run that must have accepted ``--json``."""
    assert_flag_recognised(run)
    assert_plain_usage_error(run)


ModelT = TypeVar("ModelT", bound=BaseModel)


def parse(model: type[ModelT], run: CliRun) -> ModelT:
    """Validate a run's stdout as one compact document of *model*.

    Returns:
        The validated response.
    """
    assert_flag_recognised(run)
    assert_one_compact_line(run.stdout)
    return model.model_validate_json(run.stdout)


_SVG_ID = re.compile(r"terminal-\d+")
_SVG_TITLE = re.compile(r'(class="terminal-ID-title"[^>]*>)[^<]*(</text>)')


def normalise_svg(svg: str) -> str:
    """Neutralise the two parts of a Rich SVG that depend on the command line.

    Rich names every CSS class and clip path ``terminal-<n>``, where ``<n>`` is a
    hash that includes the title, and the title is the argv. Two exports of the
    same output made with different argv therefore differ in exactly these two
    places and nowhere else.

    Returns:
        *svg* with the numeric id replaced by ``ID`` and the title text by ``TITLE``.
    """
    return _SVG_TITLE.sub(r"\1TITLE\2", _SVG_ID.sub("terminal-ID", svg))
