"""Probes for the ``--json`` contract of the ``skilllint`` CLI.

``--json`` does not exist yet. Every probe that needs it is ``xfail(strict=True)``
and fails today for one recorded reason: the flag is rejected with
``No such option: --json`` and exit 2. Each such probe's first assertion checks
exactly that, so an unrelated failure cannot hide behind the marker, and each
xfail names the migration step that makes the probe pass. When that step lands
the probe XPASSes, strict mode turns the XPASS into a failure, and the author of
the step removes the marker in the same commit.

Probes that already pass are plain tests that guard behaviour the migration must
keep: a ``--json`` before the subcommand stays rejected, and the SVG normaliser
that record comparisons rely on works on today's default output.

Everything runs the real executable as a subprocess in a pinned environment
(``cli_probe``); ``CliRunner`` is never used. The expected response shapes live in
``json_probe_support`` and come from the migration brief and spec. stderr is never
asserted to be empty: it legitimately carries policy diagnostics and, in some
checkouts, an install warning.

Contract (brief sections 5 and 8):

- stdout is exactly one compact JSON line; results exit 0 or 1; usage errors exit
  2 with plain text on stderr and an empty stdout;
- nothing Rich-rendered reaches stdout or stderr, whatever the terminal;
- ``--json`` is a per-command option; at the root it is valid only with
  ``--version``;
- ``--record`` keeps writing its file and the response carries the absolute,
  resolved ``record_path``;
- ``docs sections``, ``docs section`` and ``docs verify`` report ``file_exists``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from cli_probe import CliRun, Endpoints, Sandbox, run_cli
from default_output_cases import (
    CLOSED_TOKEN,
    CORE_VARIANTS,
    NO_ENDPOINTS,
    PAGE_MARKDOWN,
    SERVED_BODIES,
    SERVED_TOKEN,
    STALE_AGE,
    Case,
    docs_cached,
    docs_page,
    docs_page_modified,
    docs_page_unverifiable,
    empty_workspace,
    policy_workspace,
    workspace,
)
from json_probe_support import (
    AuthoritiesResponse,
    CheckResponse,
    FetchNoCacheResponse,
    FetchResponse,
    FileResponse,
    LatestFoundResponse,
    LatestNotFoundResponse,
    RecordedResponse,
    RuleFoundResponse,
    RulesResponse,
    RuleUnknownResponse,
    SectionFoundResponse,
    SectionNotFoundResponse,
    SectionsResponse,
    TokensResponse,
    VerifyResponse,
    VersionResponse,
    assert_flag_recognised,
    assert_plain,
    assert_plain_usage_error,
    assert_usage_error,
    normalise_svg,
    parse,
    run_probe,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

# --- what each probe is waiting for -----------------------------------------------

STEP_DOCS: Final = "migration step 4 (docs --json)"
STEP_RULES: Final = "migration step 5 (rules and rule --json, with --record)"
STEP_CHECK: Final = "migration step 6 (check --json)"
STEP_VERSION: Final = "migration step 7 (--version --json and the root guard)"


def pending(step: str) -> pytest.MarkDecorator:
    """Mark a probe as red until *step* lands.

    Returns:
        A strict xfail that accepts only an ``AssertionError``, so a harness
        crash or an unexpected exception stays visible as a real failure.
    """
    return pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=f"RED until {step}: --json is rejected today with 'No such option: --json' (exit 2)",
    )


LANDED_STEPS: Final = frozenset({STEP_DOCS, STEP_RULES, STEP_CHECK})
"""Steps whose probes already pass. A step is added here in the commit that lands it."""


def pending_marks(step: str) -> list[pytest.MarkDecorator]:
    """Return the strict xfail for *step*, or nothing once the step has landed."""
    return [] if step in LANDED_STEPS else [pending(step)]


def case(
    args: tuple[str, ...],
    setup: Callable[[Sandbox, Endpoints], None] = workspace,
    *,
    docs: bool = False,
    authority_urls: tuple[str, ...] | None = None,
) -> Case:
    """Build an unnamed probe case; the id only matters for baselines."""
    return Case("probe", args, setup=setup, docs=docs, authority_urls=authority_urls)


def without_json(args: tuple[str, ...]) -> tuple[str, ...]:
    """Return *args* as the default (text) invocation of the same command."""
    return tuple(arg for arg in args if arg != "--json")


PAGE_PATH: Final = "sources/page-2026-01-01-0000.md"
"""Where ``docs_page`` seeds its cached file, relative to the sandbox."""


# --- one probe per command: exit code, single compact line, exact shape -----------


@dataclass(frozen=True, slots=True)
class Probe:
    """An invocation, the exit status it must give and the shape it must print."""

    id: str
    case: Case
    exit_code: int
    model: type[BaseModel]
    step: str


def _docs_case(*args: str, setup: Callable[[Sandbox, Endpoints], None] = docs_page) -> Case:
    return case(("docs", *args, "--json"), setup, docs=True)


PROBES: Final = (
    Probe("check-pass", case(("check", "valid_skill.md", "--json")), 0, CheckResponse, STEP_CHECK),
    Probe("check-fail", case(("check", "invalid-skill/SKILL.md", "--json")), 1, CheckResponse, STEP_CHECK),
    Probe("check-plugin-dir", case(("check", "plug", "--json")), 1, CheckResponse, STEP_CHECK),
    Probe("check-fix", case(("check", "fixme/SKILL.md", "--fix", "--json")), 0, CheckResponse, STEP_CHECK),
    Probe(
        "check-platform", case(("check", "plug", "--platform", "claude-code", "--json")), 1, CheckResponse, STEP_CHECK
    ),
    Probe(
        "check-tokens-only-file",
        case(("check", "valid_skill.md", "--tokens-only", "--json")),
        0,
        TokensResponse,
        STEP_CHECK,
    ),
    Probe(
        "check-tokens-only-batch",
        case(("check", "valid_skill.md", "invalid-skill/SKILL.md", "--tokens-only", "--json")),
        0,
        TokensResponse,
        STEP_CHECK,
    ),
    Probe("rules", case(("rules", "--json")), 0, RulesResponse, STEP_RULES),
    Probe(
        "rules-no-match",
        case(("rules", "--platform", "cursor", "--category", "codex", "--json")),
        0,
        RulesResponse,
        STEP_RULES,
    ),
    Probe("rule-found", case(("rule", "FM010", "--json")), 0, RuleFoundResponse, STEP_RULES),
    Probe("rule-unknown", case(("rule", "ZZ999", "--json")), 1, RuleUnknownResponse, STEP_RULES),
    Probe("version", case(("--version", "--json")), 0, VersionResponse, STEP_VERSION),
    Probe(
        "docs-fetch-new",
        _docs_case("fetch", f"{SERVED_TOKEN}/new.md", setup=empty_workspace),
        0,
        FetchResponse,
        STEP_DOCS,
    ),
    Probe(
        "docs-fetch-no-cache",
        _docs_case("fetch", f"{CLOSED_TOKEN}/new.md", setup=empty_workspace),
        1,
        FetchNoCacheResponse,
        STEP_DOCS,
    ),
    Probe(
        "docs-fetch-authorities",
        case(
            ("docs", "fetch-authorities", "--json"),
            empty_workspace,
            docs=True,
            authority_urls=(f"{SERVED_TOKEN}/new.md", f"{CLOSED_TOKEN}/down.md"),
        ),
        1,
        AuthoritiesResponse,
        STEP_DOCS,
    ),
    Probe(
        "docs-fetch-authorities-empty-registry",
        case(("docs", "fetch-authorities", "--json"), empty_workspace, docs=True, authority_urls=()),
        0,
        AuthoritiesResponse,
        STEP_DOCS,
    ),
    Probe("docs-latest-found", _docs_case("latest", "page"), 0, LatestFoundResponse, STEP_DOCS),
    Probe("docs-latest-not-found", _docs_case("latest", "absent"), 1, LatestNotFoundResponse, STEP_DOCS),
    Probe("docs-sections", _docs_case("sections", PAGE_PATH), 0, SectionsResponse, STEP_DOCS),
    Probe("docs-section-found", _docs_case("section", PAGE_PATH, "Usage"), 0, SectionFoundResponse, STEP_DOCS),
    Probe("docs-section-not-found", _docs_case("section", PAGE_PATH, "Absent"), 1, SectionNotFoundResponse, STEP_DOCS),
    Probe("docs-verify-intact", _docs_case("verify", PAGE_PATH), 0, VerifyResponse, STEP_DOCS),
    Probe(
        "docs-verify-modified", _docs_case("verify", PAGE_PATH, setup=docs_page_modified), 1, VerifyResponse, STEP_DOCS
    ),
    Probe(
        "docs-verify-unverifiable",
        _docs_case("verify", PAGE_PATH, setup=docs_page_unverifiable),
        1,
        VerifyResponse,
        STEP_DOCS,
    ),
)

_PROBE_PARAMS: Final = [pytest.param(probe, marks=pending_marks(probe.step), id=probe.id) for probe in PROBES]


@pytest.mark.parametrize("probe", _PROBE_PARAMS)
def test_each_command_prints_one_compact_json_line_of_the_documented_shape(probe: Probe, tmp_path: Path) -> None:
    """Results exit 0 or 1 and print one compact JSON document with exactly the documented keys."""
    _, run = run_probe(tmp_path, probe.case)

    assert_flag_recognised(run)
    assert run.returncode == probe.exit_code
    parse(probe.model, run)


@pytest.mark.parametrize("probe", _PROBE_PARAMS)
def test_each_command_renders_nothing_with_rich_under_json(probe: Probe, tmp_path: Path) -> None:
    """Neither stream carries an ANSI escape or a box-drawing character."""
    _, run = run_probe(tmp_path, probe.case)

    assert_flag_recognised(run)
    assert_plain(run)


# --- environment independence ------------------------------------------------------

_ENVIRONMENT_PROBES: Final = [
    pytest.param(case(("rules", "--json")), id="rules"),
    pytest.param(case(("rule", "FM010", "--json")), id="rule"),
    pytest.param(case(("check", "plug", "--json")), id="check"),
    pytest.param(_docs_case("verify", PAGE_PATH), id="docs-verify"),
]


@pytest.mark.parametrize("probe_case", _ENVIRONMENT_PROBES)
def test_stdout_is_identical_in_every_terminal_environment(probe_case: Case, tmp_path: Path) -> None:
    """Width, colour variables, ``TERM`` and a pty must not change a byte of stdout, and none leaks Rich output."""
    runs = [run_probe(tmp_path, probe_case, root=variant.id, variant=variant)[1] for variant in CORE_VARIANTS]
    reference = runs[0]

    assert_flag_recognised(reference)
    for variant, run in zip(CORE_VARIANTS, runs, strict=True):
        assert_plain(run)
        assert run.returncode == reference.returncode, variant.id
        assert run.stdout == reference.stdout, variant.id


# --- exit 2: plain text on stderr, nothing on stdout -------------------------------


@dataclass(frozen=True, slots=True)
class UsageProbe:
    """A usage error and whether its stderr must equal the default path's stderr."""

    id: str
    args: tuple[str, ...]
    step: str
    same_stderr_as_default: bool
    message: bytes | None = None
    """Text the stderr must contain, when the default path has no such error to copy."""


_USAGE_PROBES: Final = (
    UsageProbe("check-no-paths", ("check",), STEP_CHECK, same_stderr_as_default=False, message=b"Missing argument"),
    UsageProbe("check-nonexistent-path", ("check", "nope.md"), STEP_CHECK, same_stderr_as_default=True),
    UsageProbe(
        "check-tokens-only-nonexistent-path",
        ("check", "nope.md", "--tokens-only"),
        STEP_CHECK,
        same_stderr_as_default=True,
    ),
    UsageProbe("check-unknown-file-type", ("check", "weird.xyz"), STEP_CHECK, same_stderr_as_default=True),
    UsageProbe(
        "check-check-and-fix", ("check", "valid_skill.md", "--check", "--fix"), STEP_CHECK, same_stderr_as_default=True
    ),
    UsageProbe(
        "check-fix-and-platform",
        ("check", "valid_skill.md", "--fix", "--platform", "claude-code"),
        STEP_CHECK,
        same_stderr_as_default=True,
    ),
    UsageProbe(
        "check-invalid-platform", ("check", "plug", "--platform", "bogus"), STEP_CHECK, same_stderr_as_default=True
    ),
    UsageProbe(
        "check-invalid-filter-type", ("check", "plug", "--filter-type", "foo"), STEP_CHECK, same_stderr_as_default=True
    ),
    UsageProbe(
        "check-filter-with-filter-type",
        ("check", "plug", "--filter", "skills/*", "--filter-type", "skills"),
        STEP_CHECK,
        same_stderr_as_default=True,
    ),
    UsageProbe("rules-invalid-severity", ("rules", "--severity", "bogus"), STEP_RULES, same_stderr_as_default=True),
    UsageProbe("rule-missing-argument", ("rule",), STEP_RULES, same_stderr_as_default=True),
)


@pytest.mark.parametrize(
    "probe", [pytest.param(probe, marks=pending_marks(probe.step), id=probe.id) for probe in _USAGE_PROBES]
)
def test_usage_errors_exit_2_with_plain_stderr_and_empty_stdout(probe: UsageProbe, tmp_path: Path) -> None:
    """The stdout help dump of the default path is dropped; the stderr message stays as it is."""
    _, run = run_probe(tmp_path, case((*probe.args, "--json")))

    assert_usage_error(run)
    if probe.message is not None:
        assert probe.message in run.stderr
    if probe.same_stderr_as_default:
        _, default = run_probe(tmp_path, case(probe.args), root="default")
        assert run.stderr == default.stderr


# --- --record ------------------------------------------------------------------------


def record_workspace(sandbox: Sandbox, endpoints: Endpoints) -> None:
    """Add ``real/`` and a symlink ``alias`` to it, so the resolved record path differs from the given one."""
    workspace(sandbox, endpoints)
    (sandbox.case / "real").mkdir()
    (sandbox.case / "alias").symlink_to("real", target_is_directory=True)


@dataclass(frozen=True, slots=True)
class RecordProbe:
    """A command that accepts ``--record`` and the response model it must print."""

    id: str
    args: tuple[str, ...]
    exit_code: int
    model: type[RecordedResponse]
    step: str


_RECORD_COMMANDS: Final = (
    RecordProbe("check", ("check", "invalid-skill/SKILL.md"), 1, CheckResponse, STEP_CHECK),
    RecordProbe("check-tokens-only", ("check", "invalid-skill", "--tokens-only"), 0, TokensResponse, STEP_CHECK),
    RecordProbe("rules", ("rules",), 0, RulesResponse, STEP_RULES),
    RecordProbe("rule", ("rule", "FM010"), 0, RuleFoundResponse, STEP_RULES),
)
_RECORD_SUFFIX_START: Final = {".svg": "<svg", ".html": "<!DOCTYPE html>"}


_RECORD_PARAMS: Final = [
    pytest.param(probe, suffix, marks=pending_marks(probe.step), id=f"{probe.id}{suffix}")
    for probe in _RECORD_COMMANDS
    for suffix in _RECORD_SUFFIX_START
]


@pytest.mark.parametrize(("probe", "suffix"), _RECORD_PARAMS)
def test_record_path_is_absolute_and_resolved_and_the_file_exists(
    probe: RecordProbe, suffix: str, tmp_path: Path
) -> None:
    """``record_path`` names the written file, with symlinks resolved, as an absolute path."""
    target = f"alias/out{suffix}"

    sandbox, run = run_probe(tmp_path, case((*probe.args, "--record", target, "--json"), record_workspace))

    assert_flag_recognised(run)
    assert run.returncode == probe.exit_code
    response = parse(probe.model, run)
    expected = (sandbox.case / "real" / f"out{suffix}").resolve()
    assert response.record_path == str(expected)
    assert Path(response.record_path).is_absolute()
    assert expected.read_text(encoding="utf-8").startswith(_RECORD_SUFFIX_START[suffix])


@pytest.mark.parametrize(
    "probe", [pytest.param(probe, marks=pending_marks(probe.step), id=probe.id) for probe in _RECORD_COMMANDS]
)
def test_html_record_is_byte_identical_to_the_default_path(probe: RecordProbe, tmp_path: Path) -> None:
    """HTML carries no title, so ``--json`` must not change the recorded bytes at all."""
    args = (*probe.args, "--record", "out.html")

    json_sandbox, json_run = run_probe(tmp_path, case((*args, "--json")), root="json")
    default_sandbox, _ = run_probe(tmp_path, case(args), root="default")

    assert_flag_recognised(json_run)
    assert (json_sandbox.case / "out.html").read_bytes() == (default_sandbox.case / "out.html").read_bytes()


@pytest.mark.parametrize(
    "probe", [pytest.param(probe, marks=pending_marks(probe.step), id=probe.id) for probe in _RECORD_COMMANDS]
)
def test_svg_record_differs_from_the_default_path_only_in_title_and_id(probe: RecordProbe, tmp_path: Path) -> None:
    """The SVG title is the argv, so it gains ``--json``; the Rich id hash follows the title. Nothing else changes."""
    args = (*probe.args, "--record", "out.svg")

    json_sandbox, json_run = run_probe(tmp_path, case((*args, "--json")), root="json")
    default_sandbox, _ = run_probe(tmp_path, case(args), root="default")

    assert_flag_recognised(json_run)
    json_svg = (json_sandbox.case / "out.svg").read_text(encoding="utf-8")
    default_svg = (default_sandbox.case / "out.svg").read_text(encoding="utf-8")
    assert "--json" in json_svg
    assert normalise_svg(json_svg) == normalise_svg(default_svg)


@pytest.mark.parametrize("target", ["out.svg", "out.html"])
def test_svg_normaliser_equates_default_exports_that_differ_only_in_argv(target: str, tmp_path: Path) -> None:
    """Guard for the comparison above, on today's default output: two target names, one normal form."""
    first, _ = run_probe(tmp_path, case(("check", "invalid-skill/SKILL.md", "--record", f"a-{target}")), root="a")
    second, _ = run_probe(tmp_path, case(("check", "invalid-skill/SKILL.md", "--record", f"b-{target}")), root="b")

    one = (first.case / f"a-{target}").read_text(encoding="utf-8")
    other = (second.case / f"b-{target}").read_text(encoding="utf-8")
    assert normalise_svg(one) == normalise_svg(other)
    if target.endswith(".svg"):
        assert one != other, "the raw SVGs should differ, or the normaliser is hiding nothing"


def test_unknown_rule_writes_no_record_file_and_reports_a_null_record_path(tmp_path: Path) -> None:
    """Today an unknown rule writes no file; ``record_path`` is therefore null and the exit status is 1."""
    sandbox, run = run_probe(tmp_path, case(("rule", "ZZ999", "--record", "out.svg", "--json")))

    assert_flag_recognised(run)
    assert run.returncode == 1
    response = parse(RuleUnknownResponse, run)
    assert response.record_path is None
    assert not (sandbox.case / "out.svg").exists()


@dataclass(frozen=True, slots=True)
class RecordFailure:
    """A ``--record`` invocation that exits 2 under ``--json``."""

    id: str
    args: tuple[str, ...]
    file_written: str | None
    """A relative path the default path writes even though the command exits 2; ``None`` when no file appears."""
    one_stderr_line: bool
    """The export failed after the command ran: the brief asks for exactly one plain line."""


_RECORD_FAILURES: Final = (
    RecordFailure(
        "unsupported-suffix", ("check", "invalid-skill/SKILL.md", "--record", "out.txt"), None, one_stderr_line=True
    ),
    RecordFailure(
        "unwritable-directory",
        ("check", "invalid-skill/SKILL.md", "--record", "missing-dir/out.svg"),
        None,
        one_stderr_line=True,
    ),
    RecordFailure(
        "unknown-file-type-still-writes-the-file",
        ("check", "weird.xyz", "--record", "out.svg"),
        "out.svg",
        one_stderr_line=False,
    ),
    RecordFailure(
        "invalid-platform-writes-no-file",
        ("check", "plug", "--platform", "bogus", "--record", "out.svg"),
        None,
        one_stderr_line=False,
    ),
)


@pytest.mark.parametrize("failure", [pytest.param(failure, id=failure.id) for failure in _RECORD_FAILURES])
def test_record_failures_exit_2_with_plain_stderr_and_keep_the_default_files(
    failure: RecordFailure, tmp_path: Path
) -> None:
    """Exit 2 prints nothing on stdout, no ``record_path``, and writes the same files the default path writes."""
    sandbox, run = run_probe(tmp_path, case((*failure.args, "--json")))

    assert_usage_error(run)
    if failure.one_stderr_line:
        assert len(run.stderr.decode().strip().splitlines()) == 1
    written = sorted(path.name for path in sandbox.case.glob("out.*"))
    assert written == ([Path(failure.file_written).name] if failure.file_written else [])


# --- check: listing, omitted block, fixes, tokens ------------------------------------

_SUMMARY_LINE = re.compile(r"(Total files|Passed|Failed|Warnings): (\d+)")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def check_json(tmp_path: Path, *flags: str, target: str = "plug", root: str = "run") -> CheckResponse:
    """Run ``check <target> <flags> --json`` and validate the response."""
    _, run = run_probe(tmp_path, case(("check", target, *flags, "--json")), root=root)
    return parse(CheckResponse, run)


def test_default_listing_names_the_failed_files_and_counts_the_rest(tmp_path: Path) -> None:
    """Default flags list only files with errors or warnings; the others are counted in ``omitted``."""
    response = check_json(tmp_path)

    assert response.status == "failed"
    assert [file.path for file in response.files] == ["plug/skills/bad/SKILL.md", "plug/skills/good/SKILL.md"]
    assert all(file.status == "failed" for file in response.files)
    assert response.omitted.passed_files == response.summary.total_files - len(response.files)
    assert response.fixes == []
    assert response.record_path is None


def test_summary_equals_the_default_text_summary(tmp_path: Path) -> None:
    """``summary`` carries the numbers the default ``--show-summary`` panel prints."""
    response = check_json(tmp_path)
    _, text = run_probe(tmp_path, case(("check", "plug", "--show-summary", "--no-color")), root="text")

    counts = {label: int(number) for label, number in _SUMMARY_LINE.findall(_ANSI.sub("", text.stdout.decode()))}
    assert response.summary.total_files == counts["Total files"]
    assert response.summary.passed == counts["Passed"]
    assert response.summary.failed == counts["Failed"]
    assert response.summary.passed_with_warnings == counts.get("Warnings", 0)


def test_validator_status_follows_passed_not_the_error_count(tmp_path: Path) -> None:
    """A validator with only warnings is ``passed``; the issue fields carry the text path's values in full."""
    response = check_json(tmp_path, target="invalid-skill/SKILL.md")

    (file,) = response.files
    assert file.path == "invalid-skill/SKILL.md"
    assert file.status == "failed"
    assert {validator.name: validator.status for validator in file.validators} == {
        "FrontmatterValidator": "failed",
        "DescriptionValidator": "passed",
    }
    issues = {issue.code: issue for validator in file.validators for issue in validator.issues}
    assert issues["FM010"].severity == "error"
    assert issues["FM010"].message == "Must use lowercase letters, numbers, and hyphens only"
    assert issues["FM010"].suggestion == "Use format: lowercase-with-hyphens"
    assert issues["SK005"].severity == "warning"


def test_show_progress_lists_a_passed_file_without_validators(tmp_path: Path) -> None:
    """The text path prints one ``PASSED`` line for such a file and no validators; so does the JSON."""
    response = check_json(tmp_path, "--show-progress", target="valid_skill.md")

    assert response.status == "passed"
    assert [(file.path, file.status, file.validators) for file in response.files] == [("valid_skill.md", "passed", [])]
    assert response.omitted.passed_files == 0
    assert response.omitted.passed_validators > 0, "the validators of a passed-and-listed file count as omitted"


def test_a_clean_tree_lists_nothing_and_says_how_to_see_more(tmp_path: Path) -> None:
    """With no flags a passing file is only counted, and ``retrieve_with`` names the flag that lists it."""
    response = check_json(tmp_path, target="valid_skill.md")

    assert response.status == "passed"
    assert response.files == []
    assert response.omitted.passed_files == 1
    assert "--show-progress" in response.omitted.retrieve_with


_FLAG_COMBINATIONS: Final = [
    pytest.param((), id="default"),
    pytest.param(("--verbose",), id="verbose"),
    pytest.param(("--show-progress",), id="show-progress"),
    pytest.param(("--verbose", "--show-progress"), id="verbose-and-show-progress"),
]


def _info_issue_count(response: CheckResponse) -> int:
    return sum(
        1
        for file in response.files
        for validator in file.validators
        for issue in validator.issues
        if issue.severity == "info"
    )


@pytest.mark.parametrize("flags", _FLAG_COMBINATIONS)
def test_omitted_counts_equal_what_the_fullest_listing_adds(flags: tuple[str, ...], tmp_path: Path) -> None:
    """Every hidden file and info issue is counted, and ``retrieve_with`` names exactly the flags that restore them."""
    response = check_json(tmp_path, *flags, root="run")
    fullest = check_json(tmp_path, "--verbose", "--show-progress", root="fullest")

    assert len(fullest.files) == fullest.summary.total_files
    assert response.omitted.passed_files == response.summary.total_files - len(response.files)
    assert response.omitted.info_issues == _info_issue_count(fullest) - _info_issue_count(response)
    retrieve = set(response.omitted.retrieve_with)
    assert ("--verbose" in retrieve) == (response.omitted.info_issues > 0)
    assert retrieve <= {"--verbose", "--show-progress"} - set(flags), "a flag already given restores nothing"
    if response.omitted.passed_files > 0:
        assert "--show-progress" in retrieve


def test_hidden_validators_of_listed_files_are_counted(tmp_path: Path) -> None:
    """Validators that passed silently inside a listed file are counted, not dropped."""
    response = check_json(tmp_path)
    with_progress = check_json(tmp_path, "--show-progress", root="progress")
    full = {file.path: len(file.validators) for file in with_progress.files}

    hidden = sum(full[file.path] - len(file.validators) for file in response.files)
    assert hidden > 0
    assert response.omitted.passed_validators == hidden


def test_fixes_lists_what_fix_applied_and_the_file_matches_the_default_path(tmp_path: Path) -> None:
    """``fixes`` mirrors the ``Fixes applied`` block; the edited file is the one the default path writes."""
    sandbox, run = run_probe(tmp_path, case(("check", "fixme/SKILL.md", "--fix", "--json")))
    default_sandbox, _ = run_probe(tmp_path, case(("check", "fixme/SKILL.md", "--fix")), root="default")

    response = parse(CheckResponse, run)
    assert [(fix.path, fix.validator, fix.codes, fix.description) for fix in response.fixes] == [
        (
            "fixme/SKILL.md",
            "FrontmatterValidator",
            ["FM004", "FM007"],
            "Converted tools from YAML array to comma-separated string",
        ),
        ("fixme/SKILL.md", "FrontmatterValidator", ["FM004", "FM007"], "Removed YAML multiline indicators"),
    ]
    assert (sandbox.case / "fixme/SKILL.md").read_bytes() == (default_sandbox.case / "fixme/SKILL.md").read_bytes()


def test_no_color_and_show_summary_are_accepted_and_change_nothing(tmp_path: Path) -> None:
    """``--no-color`` and ``--show-summary`` keep their place on the command and have no effect on the JSON."""
    _, plain = run_probe(tmp_path, case(("check", "plug", "--json")), root="plain")
    _, flagged = run_probe(tmp_path, case(("check", "plug", "--no-color", "--show-summary", "--json")), root="flagged")

    assert_flag_recognised(flagged)
    assert flagged.returncode == plain.returncode
    assert flagged.stdout == plain.stdout


def test_policy_diagnostics_stay_on_stderr_beside_the_json(tmp_path: Path) -> None:
    """A malformed ``.skilllint.json`` is reported as a ``Warning:`` line on stderr, not folded into the response."""
    _, run = run_probe(tmp_path, case(("check", "pol/x/SKILL.md", "--json"), policy_workspace("{")))

    parse(CheckResponse, run)
    assert b"Warning:" in run.stderr
    assert b".skilllint.json" in run.stderr
    assert b"Warning" not in run.stdout


def _default_token_lines(tmp_path: Path, args: tuple[str, ...]) -> list[tuple[str, int]]:
    _, run = run_probe(tmp_path, case(("check", *args, "--tokens-only")), root="default")
    lines = run.stdout.decode().splitlines()
    if all("\t" not in line for line in lines):
        # Explicit file arguments print one bare integer each, in argument order, without the path.
        return [(path, int(line)) for path, line in zip(args, lines, strict=True)]
    return [(path, int(count)) for count, path in (line.split("\t", 1) for line in lines)]


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("valid_skill.md",), id="single-file"),
        pytest.param(("invalid-skill",), id="skill-folder"),
        pytest.param(("valid_skill.md", "invalid-skill/SKILL.md"), id="batch"),
    ],
)
def test_tokens_only_is_always_a_list_with_the_counts_the_default_path_prints(
    args: tuple[str, ...], tmp_path: Path
) -> None:
    """One entry per resolved path, using the normalised path (a skill folder becomes its ``SKILL.md``)."""
    _, run = run_probe(tmp_path, case(("check", *args, "--tokens-only", "--json")))

    response = parse(TokensResponse, run)
    assert [(entry.path, entry.tokens) for entry in response.tokens] == _default_token_lines(tmp_path, args)


# --- docs ----------------------------------------------------------------------------------


def docs_json(
    tmp_path: Path, *args: str, setup: Callable[[Sandbox, Endpoints], None] = docs_page
) -> tuple[Sandbox, CliRun]:
    """Run ``skilllint docs <args> --json`` through the docs launcher."""
    return run_probe(tmp_path, _docs_case(*args, setup=setup))


_CACHED_SETUPS: Final = {
    "fresh": docs_cached(age=timedelta(0), content="# Cached\n"),
    "stale": docs_cached(age=STALE_AGE, content="# Cached\n"),
    "superseded": docs_cached(age=STALE_AGE, content="# Superseded\n"),
    "unchanged": docs_cached(age=STALE_AGE, content=SERVED_BODIES["/cached.md"].decode()),
}
"""Seeded ``cached`` pages: age and content decide which ``CacheStatus`` a fetch ends in."""


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    """A ``docs fetch`` scenario and the ``status`` it must report."""

    id: str
    base: str
    setup: str | None
    status: str
    extra_args: tuple[str, ...] = ()


_FETCH_OUTCOMES: Final = (
    FetchOutcome("new", SERVED_TOKEN, None, "new"),
    FetchOutcome("fresh", CLOSED_TOKEN, "fresh", "fresh"),
    FetchOutcome("refreshed", SERVED_TOKEN, "superseded", "refreshed"),
    FetchOutcome("unchanged", SERVED_TOKEN, "unchanged", "unchanged"),
    FetchOutcome("stale", CLOSED_TOKEN, "stale", "stale"),
    FetchOutcome("forced-refetch", SERVED_TOKEN, "fresh", "refreshed", ("--force",)),
)


@pytest.mark.parametrize("outcome", [pytest.param(outcome, id=outcome.id) for outcome in _FETCH_OUTCOMES])
def test_docs_fetch_reports_every_cache_status_as_a_field_not_a_stderr_line(
    outcome: FetchOutcome, tmp_path: Path
) -> None:
    """``status`` replaces the stderr status line; ``path`` names the file the default path would print."""
    page = "new.md" if outcome.setup is None else "cached.md"
    url = f"{outcome.base}/{page}"
    setup = empty_workspace if outcome.setup is None else _CACHED_SETUPS[outcome.setup]

    sandbox, run = docs_json(tmp_path, "fetch", *outcome.extra_args, url, setup=setup)

    response = parse(FetchResponse, run)
    assert run.returncode == 0
    assert response.status == outcome.status
    assert response.url.endswith(f"/{page}")
    assert response.page_name == page.removesuffix(".md")
    assert (sandbox.case / response.path).is_file()
    assert outcome.status.upper().encode() not in run.stderr


def test_docs_fetch_path_equals_what_the_default_path_prints(tmp_path: Path) -> None:
    """For a fresh cache the file is fixed, so the default stdout line and the JSON ``path`` must agree."""
    url = f"{CLOSED_TOKEN}/cached.md"
    _, run = docs_json(tmp_path, "fetch", url, setup=_CACHED_SETUPS["fresh"])
    with_default = case(("docs", "fetch", url), _CACHED_SETUPS["fresh"], docs=True)
    _, default = run_probe(tmp_path, with_default, root="default")

    response = parse(FetchResponse, run)
    assert response.path == default.stdout.decode().strip()


def test_fetch_authorities_attempts_every_url_and_reports_each(tmp_path: Path) -> None:
    """One result per registry URL, in order, and exit 1 when any failed."""
    probe = case(
        ("docs", "fetch-authorities", "--json"),
        empty_workspace,
        docs=True,
        authority_urls=(f"{SERVED_TOKEN}/new.md", f"{CLOSED_TOKEN}/down.md", f"{SERVED_TOKEN}/cached.md"),
    )

    _, run = run_probe(tmp_path, probe)

    response = parse(AuthoritiesResponse, run)
    assert run.returncode == 1
    assert response.status == "failed"
    assert [result.status for result in response.results] == ["new", "failed", "new"]
    failed = response.results[1]
    assert failed.url.endswith("/down.md")
    assert failed.path is None
    assert failed.reason


def test_docs_latest_path_equals_what_the_default_path_prints(tmp_path: Path) -> None:
    """``docs latest`` reports the same file the default path prints."""
    _, run = docs_json(tmp_path, "latest", "page")
    _, default = run_probe(tmp_path, case(("docs", "latest", "page"), docs_page, docs=True), root="default")

    response = parse(LatestFoundResponse, run)
    assert response.path == default.stdout.decode().strip() == PAGE_PATH


def test_docs_sections_lists_the_sections_with_their_line_ranges(tmp_path: Path) -> None:
    """The rows of the default table, as fields."""
    _, run = docs_json(tmp_path, "sections", PAGE_PATH)

    response = parse(SectionsResponse, run)
    assert response.file == PAGE_PATH
    assert response.file_exists is True
    assert [(s.level, s.heading, s.line_start, s.line_end) for s in response.sections] == [
        (1, "Page Title", 1, 15),
        (2, "Usage", 5, 12),
        (2, "Reference", 13, 15),
    ]


@pytest.mark.parametrize(
    ("query", "heading"),
    [pytest.param("Usage", "Usage", id="heading"), pytest.param("#reference", "Reference", id="slug")],
)
def test_docs_section_returns_the_section_text_unaltered_with_markup_literal(
    query: str, heading: str, tmp_path: Path
) -> None:
    """``text`` is the section slice of the file, byte for byte, with ``[bold]`` and ``:warning:`` left alone."""
    _, run = docs_json(tmp_path, "section", PAGE_PATH, query)
    _, default = run_probe(tmp_path, case(("docs", "section", PAGE_PATH, query), docs_page, docs=True), root="default")

    response = parse(SectionFoundResponse, run)
    lines = PAGE_MARKDOWN.splitlines(keepends=True)
    assert response.query == query
    assert response.heading == heading
    assert response.text == "".join(lines[response.line_start - 1 : response.line_end])
    assert response.text == default.stdout.decode()
    if heading == "Usage":
        assert "[bold]x[/bold] [link=http://a]t[/link] :warning:" in response.text


def test_docs_section_not_found_echoes_the_query(tmp_path: Path) -> None:
    """Exit 1 still prints a document, carrying the user's own query string."""
    _, run = docs_json(tmp_path, "section", PAGE_PATH, "Absent")

    response = parse(SectionNotFoundResponse, run)
    assert run.returncode == 1
    assert (response.query, response.file_exists) == ("Absent", True)


@dataclass(frozen=True, slots=True)
class VerifyOutcome:
    """A ``docs verify`` scenario."""

    id: str
    setup: Callable[[Sandbox, Endpoints], None]
    status: str
    exit_code: int
    has_sidecar: bool


_VERIFY_OUTCOMES: Final = (
    VerifyOutcome("intact", docs_page, "intact", 0, has_sidecar=True),
    VerifyOutcome("modified", docs_page_modified, "modified", 1, has_sidecar=True),
    VerifyOutcome("unverifiable", docs_page_unverifiable, "unverifiable", 1, has_sidecar=False),
)


@pytest.mark.parametrize("outcome", [pytest.param(outcome, id=outcome.id) for outcome in _VERIFY_OUTCOMES])
def test_docs_verify_reports_digests_and_exits_0_only_when_intact(outcome: VerifyOutcome, tmp_path: Path) -> None:
    """The panel fields become keys: computed digest and size, and the sidecar's expectations when there is a sidecar."""
    _, run = docs_json(tmp_path, "verify", PAGE_PATH, setup=outcome.setup)

    response = parse(VerifyResponse, run)
    content = PAGE_MARKDOWN if outcome.status != "modified" else PAGE_MARKDOWN + "Tampered.\n"
    assert run.returncode == outcome.exit_code
    assert response.status == outcome.status
    assert response.file_exists is True
    assert response.computed_sha256 == hashlib.sha256(content.encode()).hexdigest()
    assert response.computed_bytes == len(content.encode())
    if outcome.has_sidecar:
        assert response.expected_sha256 == hashlib.sha256(PAGE_MARKDOWN.encode()).hexdigest()
        assert response.expected_bytes == len(PAGE_MARKDOWN.encode())
    else:
        assert (response.expected_sha256, response.expected_bytes) == (None, None)


@pytest.mark.parametrize(
    ("args", "model", "exit_code"),
    [
        pytest.param(("sections", "absent.md"), SectionsResponse, 0, id="sections"),
        pytest.param(("section", "absent.md", "Usage"), SectionNotFoundResponse, 1, id="section"),
        pytest.param(("verify", "absent.md"), VerifyResponse, 1, id="verify"),
    ],
)
def test_a_missing_file_is_distinguishable_from_an_empty_one_by_file_exists(
    args: tuple[str, ...], model: type[FileResponse], exit_code: int, tmp_path: Path
) -> None:
    """The default path reports a missing file like an empty one; ``--json`` adds ``file_exists: false``."""
    _, run = docs_json(tmp_path, *args)

    response = parse(model, run)
    assert run.returncode == exit_code
    assert response.file_exists is False
    if isinstance(response, SectionsResponse):
        assert response.sections == []


@pytest.mark.parametrize(
    "subcommand", [("sections", "sources"), ("section", "sources", "Usage"), ("verify", "sources")]
)
def test_a_directory_argument_keeps_failing_as_it_does_today(subcommand: tuple[str, ...], tmp_path: Path) -> None:
    """Pre-existing behaviour, unchanged: ``IsADirectoryError``, exit 1, and no JSON on stdout."""
    _, run = docs_json(tmp_path, *subcommand)

    assert_flag_recognised(run)
    assert run.returncode == 1
    assert run.stdout == b""
    assert b"IsADirectoryError" in run.stderr


# --- version and the root --------------------------------------------------------------------


@pytest.mark.parametrize("args", [("--version", "--json"), ("--json", "--version"), ("-V", "--json")], ids=" ".join)
@pending(STEP_VERSION)
def test_version_json_prints_name_and_version_in_any_flag_order(args: tuple[str, ...], tmp_path: Path) -> None:
    """The root ``--json`` is valid with ``--version``, before or after it, long or short."""
    _, run = run_probe(tmp_path, case(args))
    _, plain = run_probe(tmp_path, case(("--version",)), root="plain")

    response = parse(VersionResponse, run)
    assert run.returncode == 0
    assert plain.stdout.decode().strip() == f"skilllint {response.version}"


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--json",), id="root-alone"),
        pytest.param(("--json", "check", "valid_skill.md"), id="before-check"),
        pytest.param(("--json", "rules"), id="before-rules"),
        pytest.param(("--json", "rule", "FM010"), id="before-rule"),
        pytest.param(("--json", "docs", "latest", "page"), id="before-docs"),
        pytest.param(("docs", "--json", "latest", "page"), id="on-the-docs-group"),
    ],
)
def test_json_placed_before_the_subcommand_is_a_usage_error_never_a_silent_no_op(
    args: tuple[str, ...], tmp_path: Path
) -> None:
    """Guard, green today and after the root option exists: it is valid only together with ``--version``."""
    sandbox = Sandbox.create(tmp_path)
    docs_page(sandbox, NO_ENDPOINTS)
    workspace(sandbox, NO_ENDPOINTS)

    run = run_cli(args, sandbox)

    assert_plain_usage_error(run)
