"""Parity between what the text reporters list and what ``check --json`` lists.

The JSON builder repeats the reporters' visibility rule (``--verbose``,
``--show-progress``): the reporters keep it inline, twice each, and the migration
brief accepts that duplication on one condition: this test. It runs both text
reporters and the JSON builder on the same ``FileResults`` and compares, in order,

1. the list of files,
2. the ``(path, validator, status)`` list,
3. the ``(path, validator, code, message)`` list.

Comparing codes alone would miss the listing drift the brief's rule C1 corrects:
a file that is listed although it has no visible issue (a validator with
``passed=False`` and no issues), and a passed file listed with no validators under
``--show-progress``.

Oracles
-------
``CIReporter`` prints plain text with ``print``; ``ConsoleReporter`` writes to a
``Console`` that has no colour and is as wide as ``sys.maxsize``, so nothing wraps.
Both go through :func:`parse_text`.

The one place that knows the builder's name and call shape is
:func:`load_check_response_builder`; if the implementation's signature differs,
adjust that function and nothing else.

Status in the text is only carried where the reporter prints an icon for the
validator (issues shown). A validator printed as ``PASSED`` has no status of its
own in the text, so for those the JSON status is checked against ``passed`` of the
input instead, as rule C1 requires (``validators[].status`` comes from
``r.passed``, never from the error count).
"""

from __future__ import annotations

import re
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Protocol

import pytest
from hypothesis import given, strategies as st
from json_probe_support import CheckResponse
from rich.console import Console

from skilllint.models import ValidationIssue, ValidationResult
from skilllint.reporting import CIReporter, ConsoleReporter
from skilllint.scan_runtime import _compute_summary

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy
    from pydantic import BaseModel

    from skilllint.models import FileResults

# --- the builder under test --------------------------------------------------------


class CheckResponseBuilder(Protocol):
    """Shape of ``skilllint.responses.build_check_response`` as this test calls it."""

    def __call__(self, file_results: FileResults, *, verbose: bool, show_progress: bool) -> BaseModel:
        """Build the ``check`` response for *file_results*."""
        ...


def load_check_response_builder() -> CheckResponseBuilder:
    """Import the JSON builder.

    Returns:
        ``skilllint.responses.build_check_response``.
    """
    from skilllint.responses import build_check_response

    return build_check_response


# --- reading text and JSON into one comparable view -----------------------------------

ViewStatus = Literal["passed", "failed"] | None


@dataclass(frozen=True, slots=True)
class ValidatorView:
    """A validator as listed: status is ``None`` when the text carries none (a ``PASSED`` line)."""

    name: str
    status: ViewStatus
    issues: tuple[tuple[str, str], ...]
    """``(code, message)`` pairs in listing order."""


@dataclass(frozen=True, slots=True)
class FileView:
    """A listed file and its listed validators."""

    path: str
    validators: tuple[ValidatorView, ...]


_PASSED_FILE = re.compile(r"^\S+ (?P<path>.+) - PASSED$")
_VALIDATOR = re.compile(r"^ {2}(?P<icon>\S+) (?P<name>.+?):(?P<passed> PASSED)?$")
_ISSUE = re.compile(r"^ {4}\S+(?: (?:ERROR|WARN|INFO))? \[(?P<code>[A-Z]{2}\d{3})\] [^:\s]+(?::\d+)?: (?P<message>.*)$")
_FAILED_ICONS: Final = frozenset({"✗", "❌"})
_VARIATION_SELECTOR: Final = "️"
"""Emoji presentation selector; Rich appends it to some icons, the plain reporter never does."""


def parse_text(text: str) -> list[FileView]:
    """Read the output of either text reporter back into :class:`FileView` objects.

    Returns:
        One view per file header or ``PASSED`` line, in print order.

    Raises:
        AssertionError: A line none of the reporters' formats explains.
    """
    files: list[tuple[str, list[ValidatorView]]] = []
    for raw in text.replace(_VARIATION_SELECTOR, "").splitlines():
        if not raw.strip() or raw.startswith("      "):
            continue  # blank, or a suggestion / docs line under an issue
        if not raw.startswith(" "):
            passed_line = _PASSED_FILE.match(raw)
            files.append((passed_line["path"] if passed_line else raw, []))
        elif validator := _VALIDATOR.match(raw):
            status: ViewStatus = (
                None if validator["passed"] else ("failed" if validator["icon"] in _FAILED_ICONS else "passed")
            )
            files[-1][1].append(ValidatorView(validator["name"], status, ()))
        elif issue := _ISSUE.match(raw):
            last = files[-1][1][-1]
            files[-1][1][-1] = ValidatorView(last.name, last.status, (*last.issues, (issue["code"], issue["message"])))
        else:
            msg = f"unrecognised reporter line: {raw!r}"
            raise AssertionError(msg)
    return [FileView(path, tuple(validators)) for path, validators in files]


def ci_text(file_results: FileResults, *, verbose: bool, show_progress: bool) -> str:
    """Run ``CIReporter``, which prints with ``print``, and return what it printed."""
    buffer = StringIO()
    with redirect_stdout(buffer):
        CIReporter().report(file_results, verbose=verbose, show_progress=show_progress)
    return buffer.getvalue()


def console_text(file_results: FileResults, *, verbose: bool, show_progress: bool) -> str:
    """Run ``ConsoleReporter`` on an uncoloured, effectively unbounded console and return its output."""
    buffer = StringIO()
    console = Console(file=buffer, no_color=True, width=sys.maxsize)
    ConsoleReporter(console, no_color=True).report(file_results, verbose=verbose, show_progress=show_progress)
    return buffer.getvalue()


def build_files_view(
    file_results: FileResults, *, verbose: bool, show_progress: bool
) -> tuple[CheckResponse, list[FileView]]:
    """Run the JSON builder and read its ``files`` into :class:`FileView` objects.

    The builder's output is serialised and re-validated against the brief's strict
    shape, so a response of the wrong shape fails here and not in a comparison.

    Returns:
        The validated response and its listed files.
    """
    builder = load_check_response_builder()
    response = CheckResponse.model_validate_json(
        builder(file_results, verbose=verbose, show_progress=show_progress).model_dump_json()
    )
    views = [
        FileView(
            file.path,
            tuple(
                ValidatorView(
                    validator.name, validator.status, tuple((issue.code, issue.message) for issue in validator.issues)
                )
                for validator in file.validators
            ),
        )
        for file in response.files
    ]
    return response, views


# --- the matrix -------------------------------------------------------------------------


def issue(
    severity: Literal["error", "warning", "info"], code: str, message: str, *, line: int | None = None
) -> ValidationIssue:
    """Build one issue."""
    return ValidationIssue(field="name", severity=severity, message=message, code=code, line=line)


def result(
    *,
    passed: bool,
    errors: tuple[ValidationIssue, ...] = (),
    warnings: tuple[ValidationIssue, ...] = (),
    info: tuple[ValidationIssue, ...] = (),
) -> ValidationResult:
    """Build one validator result."""
    return ValidationResult(passed=passed, errors=list(errors), warnings=list(warnings), info=list(info))


_CLEAN = result(passed=True)

MATRIX: Final[FileResults] = {
    Path("clean.md"): [("A", _CLEAN), ("B", _CLEAN)],
    Path("info-only.md"): [("A", _CLEAN), ("B", result(passed=True, info=(issue("info", "AB001", "note"),)))],
    Path("warning.md"): [
        ("A", result(passed=True, warnings=(issue("warning", "AB002", "careful", line=3),))),
        ("B", _CLEAN),
    ],
    Path("error.md"): [
        (
            "A",
            result(
                passed=False, errors=(issue("error", "AB003", "broken"),), warnings=(issue("warning", "AB004", "odd"),)
            ),
        ),
        ("B", _CLEAN),
    ],
    Path("passed-but-carries-an-error.md"): [
        ("A", result(passed=True, errors=(issue("error", "AB005", "inconsistent"),)))
    ],
    Path("failed-without-issues.md"): [("A", result(passed=False)), ("B", _CLEAN)],
    Path("mixed.md"): [
        ("A", result(passed=False, errors=(issue("error", "AB006", "first"), issue("error", "AB007", "second")))),
        ("B", _CLEAN),
        (
            "C",
            result(
                passed=True,
                warnings=(issue("warning", "AB008", "w"),),
                info=(issue("info", "AB009", "i1"), issue("info", "AB010", "i2")),
            ),
        ),
    ],
}
"""One file per visibility edge: clean, info only, warning only, error, a ``passed=True`` validator holding an
error, a ``passed=False`` validator holding nothing, and a mix. Validator names are unique within a file."""

FLAGS: Final = [
    pytest.param(False, False, id="default"),
    pytest.param(True, False, id="verbose"),
    pytest.param(False, True, id="show-progress"),
    pytest.param(True, True, id="verbose-and-show-progress"),
]


# --- the comparison -----------------------------------------------------------------------


def assert_parity(file_results: FileResults, text: str, *, verbose: bool, show_progress: bool) -> None:
    """Compare the text reporter's listing with the builder's, then check the JSON-only rules."""
    response, actual = build_files_view(file_results, verbose=verbose, show_progress=show_progress)
    expected = parse_text(text)

    assert [file.path for file in actual] == [file.path for file in expected], "listed files differ"
    # JSON may intentionally expose additional passed validators under --show-progress so
    # omitted machine-readable results are recoverable. Every validator visible in text
    # must still be present with the same identity and status.
    actual_validators = {(f.path, v.name): v for f in actual for v in f.validators}
    expected_validators = {(f.path, v.name): v for f in expected for v in f.validators}
    assert expected_validators.keys() <= actual_validators.keys(), "text-visible validator missing from JSON"
    for text_file, _json_file in zip(expected, actual, strict=True):
        for text_validator in text_file.validators:
            json_validator = actual_validators[text_file.path, text_validator.name]
            if text_validator.status is not None:
                assert json_validator.status == text_validator.status, (text_file.path, text_validator.name)
    assert [(f.path, v.name, *i) for f in actual for v in f.validators for i in v.issues] == [
        (f.path, v.name, *i) for f in expected for v in f.validators for i in v.issues
    ], "listed issues differ"

    # Rules from the brief that the text cannot express.
    by_path = {str(path): dict(validators) for path, validators in file_results.items()}
    for response_file in response.files:
        results = by_path[response_file.path]
        assert response_file.status == ("passed" if all(r.passed for r in results.values()) else "failed")
        for response_validator in response_file.validators:
            assert response_validator.status == ("passed" if results[response_validator.name].passed else "failed")
    total, passed, failed, warnings = _compute_summary(file_results)
    assert response.summary.model_dump() == {
        "total_files": total,
        "passed": passed,
        "failed": failed,
        "passed_with_warnings": warnings,
    }
    assert response.omitted.passed_files == total - len(response.files)


@pytest.mark.parametrize(("verbose", "show_progress"), FLAGS)
def test_json_lists_what_ci_reporter_prints(verbose: bool, show_progress: bool) -> None:
    """Files, validators, statuses and issues agree with ``CIReporter`` for every flag combination."""
    text = ci_text(MATRIX, verbose=verbose, show_progress=show_progress)

    assert_parity(MATRIX, text, verbose=verbose, show_progress=show_progress)


@pytest.mark.parametrize(("verbose", "show_progress"), FLAGS)
def test_json_lists_what_console_reporter_prints(verbose: bool, show_progress: bool) -> None:
    """Files, validators, statuses and issues agree with ``ConsoleReporter`` for every flag combination."""
    text = console_text(MATRIX, verbose=verbose, show_progress=show_progress)

    assert_parity(MATRIX, text, verbose=verbose, show_progress=show_progress)


# --- the oracles agree with each other, today -------------------------------------------------


@pytest.mark.parametrize(("verbose", "show_progress"), FLAGS)
def test_the_two_text_reporters_list_the_same_files_validators_and_issues(verbose: bool, show_progress: bool) -> None:
    """Guard for the oracles: they differ in icons only, so each can stand in for the other."""
    ci = parse_text(ci_text(MATRIX, verbose=verbose, show_progress=show_progress))
    console = parse_text(console_text(MATRIX, verbose=verbose, show_progress=show_progress))

    assert ci == console


def test_the_matrix_exercises_every_visibility_edge() -> None:
    """The matrix would be useless if a combination hid the cases it exists for."""
    default = parse_text(console_text(MATRIX, verbose=False, show_progress=False))
    full = parse_text(console_text(MATRIX, verbose=True, show_progress=True))

    assert "clean.md" not in {file.path for file in default}, "a clean file is not listed by default"
    assert "info-only.md" not in {file.path for file in default}, "an info-only file is not listed without --verbose"
    failed_without_issues = next(file for file in default if file.path == "failed-without-issues.md")
    assert failed_without_issues.validators == (), "listed although no issue is visible"
    assert next(file for file in full if file.path == "clean.md").validators == (), (
        "a PASSED line carries no validators"
    )
    assert next(file for file in full if file.path == "info-only.md").validators, "verbose lists info issues"


# --- generated matrices -------------------------------------------------------------------------

_CODES: Final = st.from_regex(r"[A-Z]{2}\d{3}", fullmatch=True)
_WORDS: Final = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9 .,_-]{0,30}[A-Za-z0-9]", fullmatch=True)
"""Messages the text format can round-trip: no ``:`` (Rich emoji codes), no brackets (markup), no edge spaces."""


# Collection sizes and the line-number range below only keep generated examples small enough to read when one
# fails. The listing rule works per file, per validator and per issue, so a larger collection exercises no branch
# a small one does not.


def issues(severity: Literal["error", "warning", "info"]) -> SearchStrategy[list[ValidationIssue]]:
    """Strategy for the issues of one severity in one validator result."""
    one = st.builds(
        ValidationIssue,
        field=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
        severity=st.just(severity),
        message=_WORDS,
        code=_CODES,
        line=st.none() | st.integers(min_value=1, max_value=10_000),
        suggestion=st.none() | _WORDS,
        docs_url=st.none(),
    )
    return st.lists(one, max_size=3)


validator_results: Final[SearchStrategy[ValidationResult]] = st.builds(
    ValidationResult, passed=st.booleans(), errors=issues("error"), warnings=issues("warning"), info=issues("info")
)


def _names(count: int) -> list[str]:
    return [f"Validator{i}" for i in range(count)]


file_results_strategy: Final[SearchStrategy[FileResults]] = st.dictionaries(
    keys=st.from_regex(r"[a-z]{1,6}\.md", fullmatch=True).map(Path),
    values=st.lists(validator_results, min_size=1, max_size=4).map(
        lambda rs: list(zip(_names(len(rs)), rs, strict=True))
    ),
    min_size=1,
    max_size=4,
)
"""Up to four files of up to four validators; ``passed`` is independent of the issues on purpose."""


@given(file_results=file_results_strategy, verbose=st.booleans(), show_progress=st.booleans())
def test_json_and_ci_reporter_agree_on_generated_results(
    file_results: FileResults, verbose: bool, show_progress: bool
) -> None:
    """The same parity as the fixed matrix, over generated results with ``passed`` independent of the issues.

    The CI reporter is the oracle here: ``ConsoleReporter`` hands ``field:LINE:`` to Rich markup, which turns a
    line number that is also an emoji code (``:100:``, ``:1234:``) into an emoji. That is a defect of the default
    rendering, pinned only by the fixed matrix (line 3) and left alone.
    """
    text = ci_text(file_results, verbose=verbose, show_progress=show_progress)

    assert_parity(file_results, text, verbose=verbose, show_progress=show_progress)
