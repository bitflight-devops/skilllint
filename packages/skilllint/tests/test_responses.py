"""Test response builders and emitted JSON."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skilllint.models import AppliedFix, ValidationIssue, ValidationResult
from skilllint.responses import (
    LatestFoundResponse,
    LatestNotFoundResponse,
    SectionFoundResponse,
    SectionNotFoundResponse,
    authority_failed,
    authority_fetched,
    build_authorities_response,
    build_check_response,
    build_fetch_no_cache_response,
    build_fetch_response,
    build_latest_response,
    build_rule_response,
    build_rules_response,
    build_section_response,
    build_sections_response,
    build_tokens_response,
    build_unknown_rule_response,
    build_verify_response,
    build_version_response,
    emit_response,
)
from skilllint.rule_registry import RuleEntry
from skilllint.vendor_cache import (
    CacheResult,
    CacheStatus,
    FoundSection,
    IntegrityResult,
    IntegrityStatus,
    MarkdownSection,
    NoCacheError,
)

if TYPE_CHECKING:
    from skilllint.models import FileResults

# --- AppliedFix as a field --------------------------------------------------------------------


def test_applied_fix_is_serialised_with_its_four_fields() -> None:
    """The existing dataclass is a field as it is: ``path`` a string, ``codes`` a list."""
    fix = AppliedFix(
        path=Path("a/SKILL.md"), validator="FrontmatterValidator", codes=("FM004", "FM007"), description="d"
    )

    response = build_check_response({}, verbose=False, show_progress=False, fixes=[fix])

    dumped = json.loads(response.model_dump_json())
    assert dumped["fixes"] == [
        {"path": "a/SKILL.md", "validator": "FrontmatterValidator", "codes": ["FM004", "FM007"], "description": "d"}
    ]


# --- check ------------------------------------------------------------------------------------


def _result(*, passed: bool, info: int = 0) -> ValidationResult:
    issues = [ValidationIssue(field="f", severity="info", message=f"i{n}", code="AB001") for n in range(info)]
    return ValidationResult(passed=passed, errors=[], warnings=[], info=issues)


def test_retrieve_with_names_only_flags_that_were_not_given_and_would_restore_something() -> None:
    """``--verbose`` is named for hidden info issues, ``--show-progress`` for hidden files; a given flag is not."""
    results: FileResults = {Path("a.md"): [("V", _result(passed=True, info=2))]}

    default = build_check_response(results, verbose=False, show_progress=False).omitted
    verbose = build_check_response(results, verbose=True, show_progress=False).omitted
    progress = build_check_response(results, verbose=False, show_progress=True).omitted

    assert (default.passed_files, default.info_issues, default.retrieve_with) == (
        1,
        2,
        ["--show-progress", "--verbose"],
    )
    assert (verbose.passed_files, verbose.info_issues, verbose.retrieve_with) == (0, 0, [])
    assert (progress.passed_files, progress.info_issues, progress.retrieve_with) == (0, 2, ["--verbose"])


def test_a_clean_run_omits_nothing_and_has_no_flags_to_suggest() -> None:
    """An empty result set is a passed run with an empty ``omitted`` block."""
    response = build_check_response({}, verbose=False, show_progress=False)

    assert response.status == "passed"
    assert (response.omitted.passed_files, response.omitted.passed_validators, response.omitted.info_issues) == (
        0,
        0,
        0,
    )
    assert response.omitted.retrieve_with == []


def test_record_path_and_fixes_are_carried_as_given() -> None:
    """The builder prints the record path it is given and does not resolve it."""
    response = build_check_response({}, verbose=False, show_progress=False, record_path="/abs/out.svg")

    assert response.record_path == "/abs/out.svg"


def test_tokens_response_is_a_list_even_for_one_path() -> None:
    """One entry per resolved path."""
    response = build_tokens_response([(12, Path("a/SKILL.md"))])

    assert [(entry.path, entry.tokens) for entry in response.tokens] == [("a/SKILL.md", 12)]
    assert response.record_path is None


# --- rules ------------------------------------------------------------------------------------


def _rule(docstring: str) -> RuleEntry:
    return RuleEntry(id="AB001", severity="warning", category="skill", platforms=["agentskills"], docstring=docstring)


@pytest.mark.parametrize(
    ("docstring", "summary"),
    [("# Title line\nmore", "Title line"), ("plain first line\nmore", "plain first line"), ("", "")],
)
def test_rule_summary_is_the_first_line_without_heading_marks(docstring: str, summary: str) -> None:
    """The same shortening ``skilllint rules`` applies to its table, said in ``summary_note``."""
    response = build_rules_response([_rule(docstring)])

    assert response.rules[0].summary == summary
    assert "skilllint rule <id>" in response.summary_note


def test_rule_response_carries_the_resolved_documentation_in_full() -> None:
    """``documentation`` is the text it is given, untouched."""
    entry = _rule("# T\n" + "x" * 5000)

    response = build_rule_response(entry, documentation="resolved\n[bold]x[/bold]", record_path="/r.svg")

    assert response.documentation == "resolved\n[bold]x[/bold]"
    assert (response.id, response.platforms, response.record_path) == ("AB001", ["agentskills"], "/r.svg")


def test_unknown_rule_response_names_the_listing_command_and_never_a_record() -> None:
    """``record_path`` is always null: no file is written for an unknown rule."""
    dumped = json.loads(build_unknown_rule_response("ZZ999").model_dump_json())

    assert dumped == {
        "command": "rule",
        "status": "unknown",
        "rule_id": "ZZ999",
        "list_command": "skilllint rules",
        "record_path": None,
    }


# --- docs -------------------------------------------------------------------------------------


def test_fetch_responses_map_the_cache_result_and_the_error() -> None:
    """``status`` is the ``CacheStatus`` value; a missing cache is its own shape."""
    produced = build_fetch_response(
        CacheResult(path=Path("s/p.md"), status=CacheStatus.REFRESHED, page_name="p", url="u")
    )
    missing = build_fetch_no_cache_response(NoCacheError("u", "down"))

    assert json.loads(produced.model_dump_json()) == {
        "command": "docs fetch",
        "status": "refreshed",
        "path": "s/p.md",
        "page_name": "p",
        "url": "u",
    }
    assert json.loads(missing.model_dump_json()) == {
        "command": "docs fetch",
        "status": "no_cache",
        "url": "u",
        "reason": "down",
    }


def test_authorities_response_is_failed_when_any_url_failed_and_ok_when_empty() -> None:
    """Every URL gets an entry; an empty registry is ``ok``."""
    fetched = authority_fetched("u1", CacheResult(path=Path("p.md"), status=CacheStatus.NEW, page_name="p", url="u1"))
    failed = authority_failed("u2", "boom")

    mixed = build_authorities_response([fetched, failed])
    empty = build_authorities_response([])

    assert (mixed.status, [r.status for r in mixed.results]) == ("failed", [CacheStatus.NEW, "failed"])
    assert (failed.path, failed.page_name, failed.reason) == (None, None, "boom")
    assert (empty.status, empty.results) == ("ok", [])


def test_latest_response_is_found_or_not_found() -> None:
    """The two shapes of ``docs latest``."""
    assert isinstance(build_latest_response("p", Path("s/p.md")), LatestFoundResponse)
    assert isinstance(build_latest_response("p", None), LatestNotFoundResponse)


def test_section_responses_carry_the_query_and_file_exists() -> None:
    """``file_exists`` is reported on every file-reading response; ``query`` is the user's string."""
    section = MarkdownSection(heading="Usage", level=2, line_start=5, line_end=12)

    found = build_section_response(Path("f.md"), "#usage", FoundSection(section=section, text="t"), file_exists=True)
    missing = build_section_response(Path("f.md"), "nope", None, file_exists=False)
    listing = build_sections_response(Path("f.md"), [section], file_exists=True)

    assert isinstance(found, SectionFoundResponse)
    assert (found.query, found.heading, found.text) == ("#usage", "Usage", "t")
    assert isinstance(missing, SectionNotFoundResponse)
    assert (missing.query, missing.file_exists) == ("nope", False)
    assert [(s.level, s.heading, s.line_start, s.line_end) for s in listing.sections] == [(2, "Usage", 5, 12)]


def test_verify_response_has_null_expectations_without_a_sidecar() -> None:
    """The ``expected_*`` fields are null for an unverifiable file."""
    result = IntegrityResult(
        status=IntegrityStatus.UNVERIFIABLE,
        file_path=Path("f.md"),
        computed_sha256="abc",
        expected_sha256=None,
        computed_bytes=3,
        expected_bytes=None,
    )

    dumped = json.loads(build_verify_response(result, file_exists=True).model_dump_json())

    assert dumped["status"] == "unverifiable"
    assert (dumped["expected_sha256"], dumped["expected_bytes"]) == (None, None)


# --- output -----------------------------------------------------------------------------------


def test_emit_response_writes_one_compact_ascii_safe_line() -> None:
    """Non-ASCII is escaped so surrogateescaped POSIX paths remain reversible JSON."""
    buffer = io.StringIO()

    with redirect_stdout(buffer):
        emit_response(build_version_response("1.0.0-é"))

    assert buffer.getvalue() == '{"command":"version","name":"skilllint","version":"1.0.0-\\u00e9"}\n'


def test_emit_response_round_trips_ordinary_content() -> None:
    """Escaping changes representation, not the parsed response data."""
    response = build_rules_response([_rule('# T "q" \\ \t tab \u2028 é 𝄞\x01\n' + "x" * 50)])
    buffer = io.StringIO()

    with redirect_stdout(buffer):
        emit_response(response)

    assert json.loads(buffer.getvalue()) == response.model_dump(mode="json")
