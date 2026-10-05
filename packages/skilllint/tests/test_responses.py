"""Unit tests for ``skilllint.responses``: schemas, round-trips, builders and the stdout writer.

``test_check_json_parity`` covers what ``check`` lists. This module covers the rest of the
module: every response model keeps its documented schema (snapshots), survives a JSON round trip
(Hypothesis), and the pure builders map the domain objects they read onto the documented fields.

Schema snapshots live in ``response_schemas/<Model>.json``. A deliberate schema change is
reviewed by regenerating them with::

    uv run python -m test_responses

run from ``packages/skilllint/tests``.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING, Final, no_type_check

import pytest
from hypothesis import given, strategies as st

from skilllint import responses
from skilllint.models import AppliedFix, ValidationIssue, ValidationResult
from skilllint.responses import (
    AuthoritiesResponse,
    CheckResponse,
    FetchNoCacheResponse,
    FetchResponse,
    LatestFoundResponse,
    LatestNotFoundResponse,
    Response,
    RuleFoundResponse,
    RulesResponse,
    RuleUnknownResponse,
    SectionFoundResponse,
    SectionNotFoundResponse,
    SectionsResponse,
    TokensResponse,
    VerifyResponse,
    VersionResponse,
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

SNAPSHOTS: Final = Path(__file__).parent / "response_schemas"

RESPONSE_MODELS: Final[tuple[type[Response], ...]] = (
    AuthoritiesResponse,
    CheckResponse,
    FetchNoCacheResponse,
    FetchResponse,
    LatestFoundResponse,
    LatestNotFoundResponse,
    RuleFoundResponse,
    RuleUnknownResponse,
    RulesResponse,
    SectionFoundResponse,
    SectionNotFoundResponse,
    SectionsResponse,
    TokensResponse,
    VerifyResponse,
    VersionResponse,
)


def schema_text(model: type[Response]) -> str:
    """Return the snapshot text of *model*'s JSON schema: sorted keys, indented, one trailing newline."""
    return json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize("model", RESPONSE_MODELS, ids=lambda model: model.__name__)
def test_schema_matches_the_snapshot(model: type[Response]) -> None:
    """The documented shape of each response is pinned; a change must be a reviewed snapshot update."""
    assert (SNAPSHOTS / f"{model.__name__}.json").read_text(encoding="utf-8") == schema_text(model)


def test_every_snapshot_belongs_to_a_response_model() -> None:
    """No snapshot is left over from a removed model."""
    assert {path.stem for path in SNAPSHOTS.glob("*.json")} == {model.__name__ for model in RESPONSE_MODELS}


def test_every_public_response_model_is_snapshotted() -> None:
    """A new top-level response added to the module must be added to ``RESPONSE_MODELS``."""
    top_level = {
        obj
        for name, obj in vars(responses).items()
        if name.endswith("Response") and isinstance(obj, type) and issubclass(obj, Response)
    }
    assert top_level - {Response} == set(RESPONSE_MODELS) | {responses.RecordedResponse}


# --- round trips ------------------------------------------------------------------------------

_CODES: Final = st.from_regex(r"[A-Z]{2}\d{3}", fullmatch=True)
_ISSUES: Final = st.builds(
    ValidationIssue,
    field=st.text(),
    severity=st.sampled_from(["error", "warning", "info"]),
    message=st.text(),
    code=_CODES,
    line=st.none() | st.integers(),
    suggestion=st.none() | st.text(),
    docs_url=st.none() | st.text(),
)
_FIXES: Final = st.builds(
    AppliedFix, path=st.text().map(Path), validator=st.text(), codes=st.lists(_CODES).map(tuple), description=st.text()
)


@pytest.fixture(autouse=True, scope="module")
def _register_strategies() -> None:  # pragma: no cover - registration only
    """Teach ``from_type`` the two domain types whose fields carry a pattern or a ``Path``."""
    st.register_type_strategy(ValidationIssue, _ISSUES)
    st.register_type_strategy(AppliedFix, _FIXES)


@pytest.mark.parametrize("model", RESPONSE_MODELS, ids=lambda model: model.__name__)
@given(data=st.data())
def test_response_survives_a_json_round_trip(model: type[Response], data: st.DataObject) -> None:
    """Dumping and validating again gives an equal model, and the dump is one line."""
    response = data.draw(st.from_type(model))

    dumped = response.model_dump_json()

    assert "\n" not in dumped
    assert model.model_validate_json(dumped) == response


def test_an_unknown_key_is_rejected() -> None:
    """``extra="forbid"`` holds: a key the model does not declare fails validation."""
    good = build_version_response("1.0.0").model_dump()

    with pytest.raises(ValueError, match="extra"):
        VersionResponse.model_validate({**good, "surprise": 1})


@no_type_check  # Assigning to a frozen field is the violation under test; the type checker rightly rejects it.
def assign_version(response: VersionResponse) -> None:
    """Try to change a built response."""
    response.version = "2.0.0"


def test_responses_are_frozen() -> None:
    """A built response cannot be altered before it is printed."""
    with pytest.raises(ValueError, match="frozen"):
        assign_version(build_version_response("1.0.0"))


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
    assert CheckResponse.model_validate_json(response.model_dump_json()).fixes == [fix]


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


def test_emit_response_writes_one_compact_line_with_non_ascii_as_utf8() -> None:
    """``model_dump_json()`` plus one newline, nothing else, and no ``\\u`` escape for non-ASCII."""
    buffer = io.StringIO()

    with redirect_stdout(buffer):
        emit_response(build_version_response("1.0.0-é"))

    assert buffer.getvalue() == '{"command":"version","name":"skilllint","version":"1.0.0-é"}\n'


if __name__ == "__main__":
    SNAPSHOTS.mkdir(exist_ok=True)
    for stale in SNAPSHOTS.glob("*.json"):
        stale.unlink()
    for model in RESPONSE_MODELS:
        (SNAPSHOTS / f"{model.__name__}.json").write_text(schema_text(model), encoding="utf-8")
