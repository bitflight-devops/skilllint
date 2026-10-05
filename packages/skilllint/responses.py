"""Typed ``--json`` responses of the ``skilllint`` CLI, and the one function that prints them.

An agent that runs ``skilllint <command> --json`` reads exactly one line of compact JSON on
stdout. This module owns that contract: the frozen Pydantic response models, the pure builders
that fill them from the same typed domain objects the human-facing reporters already read
(:data:`skilllint.models.FileResults`, :class:`skilllint.rule_registry.RuleEntry`, the
:mod:`skilllint.vendor_cache` results), and :func:`emit_response`.

The module is deliberately free of Rich and of the CLI. It imports only Pydantic, the
dependency-light :mod:`skilllint.models`, :mod:`skilllint.rule_registry` and
:mod:`skilllint.vendor_cache`, so the response layer stays testable on its own and cannot
render anything.

Contract:

- Every model is frozen and rejects unknown keys. ``command`` is a ``Literal`` and names the
  response.
- ``check``, ``check --tokens-only``, ``rules`` and a found ``rule`` carry ``record_path``, always
  present as the last key: the absolute, resolved path of the ``--record`` file, or ``null``.
- Nothing is truncated. Where ``check`` leaves items out of ``files`` it says what and which
  flag restores it (:class:`Omitted`).
- The builders do no I/O and take paths already in the form to be printed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final, Literal

from pydantic import BaseModel, ConfigDict

from skilllint.models import AppliedFix, ValidationIssue
from skilllint.vendor_cache import CacheStatus, IntegrityStatus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from skilllint.models import FileResults, ValidationResult
    from skilllint.rule_registry import RuleEntry
    from skilllint.vendor_cache import CacheResult, FoundSection, IntegrityResult, MarkdownSection, NoCacheError

__all__ = [
    "AuthoritiesResponse",
    "AuthorityResult",
    "CheckResponse",
    "CheckSummary",
    "CheckedFile",
    "CheckedValidator",
    "FetchNoCacheResponse",
    "FetchResponse",
    "LatestFoundResponse",
    "LatestNotFoundResponse",
    "Omitted",
    "Response",
    "RuleFoundResponse",
    "RuleRow",
    "RuleUnknownResponse",
    "RulesResponse",
    "SectionEntry",
    "SectionFoundResponse",
    "SectionNotFoundResponse",
    "SectionsResponse",
    "TokenCount",
    "TokensResponse",
    "VerifyResponse",
    "VersionResponse",
    "authority_failed",
    "authority_fetched",
    "build_authorities_response",
    "build_check_response",
    "build_fetch_no_cache_response",
    "build_fetch_response",
    "build_latest_response",
    "build_rule_response",
    "build_rules_response",
    "build_section_response",
    "build_sections_response",
    "build_tokens_response",
    "build_unknown_rule_response",
    "build_verify_response",
    "build_version_response",
    "emit_response",
]

SHOW_PROGRESS_FLAG: Final = "--show-progress"
"""The ``check`` flag that lists passed files and validators."""

VERBOSE_FLAG: Final = "--verbose"
"""The ``check`` flag that lists info issues."""

RULES_SUMMARY_NOTE: Final = (
    "summary is the first line of the rule documentation; run `skilllint rule <id>` for the full text"
)
"""Said in every ``rules`` response, because ``summary`` shortens the rule documentation."""

RULES_LIST_COMMAND: Final = "skilllint rules"
"""The command that lists every rule id, named by an unknown-rule response."""

Status = Literal["passed", "failed"]


class Response(BaseModel):
    """Base of every response: frozen, and no key that the model does not declare."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --- check ------------------------------------------------------------------------------------


class CheckSummary(Response):
    """Counts over every file that was checked, listed or not.

    ``passed_with_warnings`` is what ``scan_runtime._compute_summary`` calls ``warnings``: the
    passed files that carry at least one warning.
    """

    total_files: int
    passed: int
    failed: int
    passed_with_warnings: int


class CheckedValidator(Response):
    """One validator listed inside a file; ``status`` is the validator's own ``passed``."""

    name: str
    status: Status
    issues: list[ValidationIssue]


class CheckedFile(Response):
    """One listed file; ``path`` is exactly what the text reporters print."""

    path: str
    status: Status
    validators: list[CheckedValidator]


class Omitted(Response):
    """What ``files`` left out, and the flags that bring it back.

    All counts are 0 and ``retrieve_with`` is empty when nothing was left out. A flag that was
    already given is never named, because it restores nothing.
    """

    passed_files: int
    passed_validators: int
    info_issues: int
    retrieve_with: list[Literal["--show-progress", "--verbose"]]


class CheckResponse(Response):
    """``skilllint check --json``."""

    command: Literal["check"] = "check"
    status: Status
    summary: CheckSummary
    files: list[CheckedFile]
    fixes: list[AppliedFix]
    omitted: Omitted
    record_path: str | None = None


class TokenCount(Response):
    """Body token count of one resolved path."""

    path: str
    tokens: int


class TokensResponse(Response):
    """``skilllint check --tokens-only --json``: one entry per resolved path, always a list."""

    command: Literal["check --tokens-only"] = "check --tokens-only"
    tokens: list[TokenCount]
    record_path: str | None = None


def _visible_issues(result: ValidationResult, *, verbose: bool) -> list[ValidationIssue]:
    """Return the issues the text reporters print for *result*: errors, warnings, and info when *verbose*."""
    issues = [*result.errors, *result.warnings]
    if verbose:
        issues.extend(result.info)
    return issues


def _summarize(file_results: FileResults) -> CheckSummary:
    """Count files by outcome with the rule of ``scan_runtime._compute_summary``.

    ``test_check_json_parity`` compares the two, so the rule cannot drift unnoticed.

    Returns:
        The counts over every file in *file_results*.
    """
    passed = 0
    failed = 0
    with_warnings = 0
    for validator_results in file_results.values():
        if all(result.passed for _, result in validator_results):
            passed += 1
            if any(result.warnings for _, result in validator_results):
                with_warnings += 1
        else:
            failed += 1
    return CheckSummary(total_files=len(file_results), passed=passed, failed=failed, passed_with_warnings=with_warnings)


def _retrieve_with(
    omitted_files: int, omitted_validators: int, omitted_info: int, *, verbose: bool, show_progress: bool
) -> list[Literal["--show-progress", "--verbose"]]:
    """Name the flags that would restore what was left out, skipping flags already given.

    Returns:
        ``--show-progress`` when files or validators were left out, ``--verbose`` when info issues were.
    """
    flags: list[Literal["--show-progress", "--verbose"]] = []
    if not show_progress and (omitted_files or omitted_validators):
        flags.append(SHOW_PROGRESS_FLAG)
    if not verbose and omitted_info:
        flags.append(VERBOSE_FLAG)
    return flags


def build_check_response(
    file_results: FileResults,
    *,
    verbose: bool,
    show_progress: bool,
    fixes: Sequence[AppliedFix] = (),
    record_path: str | None = None,
) -> CheckResponse:
    """Build the ``check`` response, listing what ``ConsoleReporter`` and ``CIReporter`` print.

    A file is listed in full unless every validator passed and none has a visible issue. Under
    *show_progress* such a file is listed with no validators, the way the reporters print one
    ``PASSED`` line for it. Inside a listed file a validator appears when it has a visible issue
    or *show_progress* is set. Statuses come from ``ValidationResult.passed``, never from the
    number of errors. Everything not listed is counted in :class:`Omitted`.

    Args:
        file_results: Results per file, as the reporters receive them.
        verbose: Whether info issues are visible.
        show_progress: Whether passed files and validators are listed.
        fixes: Fixes ``--fix`` applied, in the order they were recorded.
        record_path: Absolute, resolved path of the ``--record`` file, when one was written.

    Returns:
        The response, which is ``failed`` exactly when a file failed.
    """
    files: list[CheckedFile] = []
    omitted_files = 0
    omitted_validators = 0
    omitted_info = 0 if verbose else sum(len(r.info) for results in file_results.values() for _, r in results)

    for file_path, validator_results in file_results.items():
        all_passed = all(result.passed for _, result in validator_results)
        any_visible = any(_visible_issues(result, verbose=verbose) for _, result in validator_results)
        if all_passed and not any_visible:
            if show_progress:
                files.append(CheckedFile(path=str(file_path), status="passed", validators=[]))
                omitted_validators += len(validator_results)
            else:
                omitted_files += 1
            continue

        validators: list[CheckedValidator] = []
        for name, result in validator_results:
            issues = _visible_issues(result, verbose=verbose)
            if issues or show_progress:
                validators.append(
                    CheckedValidator(name=name, status="passed" if result.passed else "failed", issues=issues)
                )
            else:
                omitted_validators += 1
        files.append(
            CheckedFile(path=str(file_path), status="passed" if all_passed else "failed", validators=validators)
        )

    summary = _summarize(file_results)
    return CheckResponse(
        status="failed" if summary.failed else "passed",
        summary=summary,
        files=files,
        fixes=list(fixes),
        omitted=Omitted(
            passed_files=omitted_files,
            passed_validators=omitted_validators,
            info_issues=omitted_info,
            retrieve_with=_retrieve_with(
                omitted_files, omitted_validators, omitted_info, verbose=verbose, show_progress=show_progress
            ),
        ),
        record_path=record_path,
    )


def build_tokens_response(entries: Sequence[tuple[int, Path]], *, record_path: str | None = None) -> TokensResponse:
    """Build the ``check --tokens-only`` response.

    Args:
        entries: ``(token count, normalised path)`` per resolved path, in the order they were counted.
        record_path: Absolute, resolved path of the ``--record`` file, when one was written.

    Returns:
        The response, with one entry per path even for a single path.
    """
    return TokensResponse(
        tokens=[TokenCount(path=str(path), tokens=count) for count, path in entries], record_path=record_path
    )


# --- rules ------------------------------------------------------------------------------------


class RuleRow(Response):
    """One row of the rules table, with the table's own shortening of ``summary``."""

    id: str
    severity: Literal["error", "warning", "info"]
    category: str
    fixable: bool
    summary: str


class RulesResponse(Response):
    """``skilllint rules --json``; no match is an empty ``rules`` list."""

    command: Literal["rules"] = "rules"
    rules: list[RuleRow]
    summary_note: str = RULES_SUMMARY_NOTE
    record_path: str | None = None


class RuleFoundResponse(Response):
    """``skilllint rule <known id> --json``; ``documentation`` is raw, unwrapped Markdown."""

    command: Literal["rule"] = "rule"
    status: Literal["found"] = "found"
    id: str
    severity: Literal["error", "warning", "info"]
    category: str
    platforms: list[str]
    documentation: str
    record_path: str | None = None


class RuleUnknownResponse(Response):
    """``skilllint rule <unknown id> --json``; no file is ever recorded, so ``record_path`` is null."""

    command: Literal["rule"] = "rule"
    status: Literal["unknown"] = "unknown"
    rule_id: str
    list_command: Literal["skilllint rules"] = RULES_LIST_COMMAND
    record_path: None = None


def _rule_summary(entry: RuleEntry) -> str:
    """Return the first docstring line without Markdown heading marks, as the rules table shows it."""
    return entry.docstring.split("\n")[0].lstrip("#").strip() if entry.docstring else ""


def build_rules_response(rules: Sequence[RuleEntry], *, record_path: str | None = None) -> RulesResponse:
    """Build the ``rules`` response.

    Args:
        rules: The rules to list, already filtered, in table order.
        record_path: Absolute, resolved path of the ``--record`` file, when one was written.

    Returns:
        The response.
    """
    return RulesResponse(
        rules=[
            RuleRow(
                id=rule.id,
                severity=rule.severity,
                category=rule.category,
                fixable=rule.fixable,
                summary=_rule_summary(rule),
            )
            for rule in rules
        ],
        record_path=record_path,
    )


def build_rule_response(entry: RuleEntry, *, documentation: str, record_path: str | None = None) -> RuleFoundResponse:
    """Build the response for a known rule.

    Args:
        entry: The registry entry.
        documentation: The rule's docstring with its example markers resolved.
        record_path: Absolute, resolved path of the ``--record`` file, when one was written.

    Returns:
        The response.
    """
    return RuleFoundResponse(
        id=entry.id,
        severity=entry.severity,
        category=entry.category,
        platforms=list(entry.platforms),
        documentation=documentation,
        record_path=record_path,
    )


def build_unknown_rule_response(rule_id: str) -> RuleUnknownResponse:
    """Build the response for a rule id the registry does not know.

    Args:
        rule_id: The id as the user typed it.

    Returns:
        The response.
    """
    return RuleUnknownResponse(rule_id=rule_id)


# --- version ----------------------------------------------------------------------------------


class VersionResponse(Response):
    """``skilllint --version --json``."""

    command: Literal["version"] = "version"
    name: Literal["skilllint"] = "skilllint"
    version: str


def build_version_response(version: str) -> VersionResponse:
    """Build the ``--version`` response.

    Args:
        version: The installed version.

    Returns:
        The response.
    """
    return VersionResponse(version=version)


# --- docs -------------------------------------------------------------------------------------


class FetchResponse(Response):
    """``skilllint docs fetch --json`` when a file was produced; ``status`` replaces the stderr status line."""

    command: Literal["docs fetch"] = "docs fetch"
    status: CacheStatus
    path: str
    page_name: str
    url: str


class FetchNoCacheResponse(Response):
    """``skilllint docs fetch --json`` when no cache exists and the network failed (exit 1)."""

    command: Literal["docs fetch"] = "docs fetch"
    status: Literal["no_cache"] = "no_cache"
    url: str
    reason: str


class AuthorityResult(Response):
    """Outcome of one registry URL inside ``docs fetch-authorities``."""

    url: str
    status: CacheStatus | Literal["failed"]
    path: str | None
    page_name: str | None
    reason: str | None


class AuthoritiesResponse(Response):
    """``skilllint docs fetch-authorities --json``; ``failed`` when any URL failed (exit 1)."""

    command: Literal["docs fetch-authorities"] = "docs fetch-authorities"
    status: Literal["ok", "failed"]
    results: list[AuthorityResult]


class LatestFoundResponse(Response):
    """``skilllint docs latest --json`` with a match."""

    command: Literal["docs latest"] = "docs latest"
    status: Literal["found"] = "found"
    page_name: str
    path: str


class LatestNotFoundResponse(Response):
    """``skilllint docs latest --json`` without a match (exit 1)."""

    command: Literal["docs latest"] = "docs latest"
    status: Literal["not_found"] = "not_found"
    page_name: str


class SectionEntry(Response):
    """One section of a markdown file; the preamble is ``heading: ""`` and ``level: 0``."""

    level: int
    heading: str
    line_start: int
    line_end: int


class SectionsResponse(Response):
    """``skilllint docs sections --json``.

    ``file_exists`` is JSON-only: the default output reports a missing file like an empty one.
    """

    command: Literal["docs sections"] = "docs sections"
    file: str
    file_exists: bool
    sections: list[SectionEntry]


class SectionFoundResponse(Response):
    """``skilllint docs section --json`` with a match; ``text`` is the section slice, unaltered."""

    command: Literal["docs section"] = "docs section"
    status: Literal["found"] = "found"
    file: str
    file_exists: bool
    query: str
    heading: str
    level: int
    line_start: int
    line_end: int
    text: str


class SectionNotFoundResponse(Response):
    """``skilllint docs section --json`` without a match (exit 1); ``query`` is the user's own string."""

    command: Literal["docs section"] = "docs section"
    status: Literal["not_found"] = "not_found"
    file: str
    file_exists: bool
    query: str


class VerifyResponse(Response):
    """``skilllint docs verify --json``; exit 0 only when ``status`` is ``intact``.

    The ``expected_*`` fields are null when there is no sidecar.
    """

    command: Literal["docs verify"] = "docs verify"
    status: IntegrityStatus
    file: str
    file_exists: bool
    computed_sha256: str
    computed_bytes: int
    expected_sha256: str | None
    expected_bytes: int | None


def build_fetch_response(result: CacheResult) -> FetchResponse:
    """Build the ``docs fetch`` response for a produced file.

    Args:
        result: What :func:`skilllint.vendor_cache.fetch_or_cached` returned.

    Returns:
        The response.
    """
    return FetchResponse(status=result.status, path=str(result.path), page_name=result.page_name, url=result.url)


def build_fetch_no_cache_response(error: NoCacheError) -> FetchNoCacheResponse:
    """Build the ``docs fetch`` response for a URL with no cache and no network.

    Args:
        error: The error :func:`skilllint.vendor_cache.fetch_or_cached` raised.

    Returns:
        The response.
    """
    return FetchNoCacheResponse(url=str(error.url), reason=str(error.reason))


def authority_fetched(url: str, result: CacheResult) -> AuthorityResult:
    """Describe a registry URL that produced a file.

    Args:
        url: The registry URL, as listed.
        result: What :func:`skilllint.vendor_cache.fetch_or_cached` returned for it.

    Returns:
        The per-URL outcome.
    """
    return AuthorityResult(
        url=url, status=result.status, path=str(result.path), page_name=result.page_name, reason=None
    )


def authority_failed(url: str, reason: str) -> AuthorityResult:
    """Describe a registry URL that could not be fetched.

    Args:
        url: The registry URL, as listed.
        reason: Why it failed.

    Returns:
        The per-URL outcome.
    """
    return AuthorityResult(url=url, status="failed", path=None, page_name=None, reason=reason)


def build_authorities_response(results: Sequence[AuthorityResult]) -> AuthoritiesResponse:
    """Build the ``docs fetch-authorities`` response.

    Args:
        results: One outcome per registry URL, in registry order. May be empty.

    Returns:
        The response, ``failed`` when any outcome failed.
    """
    failed = any(result.status == "failed" for result in results)
    return AuthoritiesResponse(status="failed" if failed else "ok", results=list(results))


def build_latest_response(page_name: str, path: Path | None) -> LatestFoundResponse | LatestNotFoundResponse:
    """Build the ``docs latest`` response.

    Args:
        page_name: The page name the user asked for.
        path: The newest cached file, or ``None`` when there is none.

    Returns:
        A found or not-found response.
    """
    if path is None:
        return LatestNotFoundResponse(page_name=page_name)
    return LatestFoundResponse(page_name=page_name, path=str(path))


def build_sections_response(
    file_path: Path, sections: Sequence[MarkdownSection], *, file_exists: bool
) -> SectionsResponse:
    """Build the ``docs sections`` response.

    Args:
        file_path: The file argument, as given.
        sections: The sections found; empty for a missing or empty file.
        file_exists: Whether the file existed before it was read.

    Returns:
        The response.
    """
    return SectionsResponse(
        file=str(file_path),
        file_exists=file_exists,
        sections=[
            SectionEntry(level=s.level, heading=s.heading, line_start=s.line_start, line_end=s.line_end)
            for s in sections
        ],
    )


def build_section_response(
    file_path: Path, query: str, found: FoundSection | None, *, file_exists: bool
) -> SectionFoundResponse | SectionNotFoundResponse:
    """Build the ``docs section`` response.

    Args:
        file_path: The file argument, as given.
        query: The heading or slug the user asked for, as typed.
        found: The matched section and its text, or ``None`` when nothing matched.
        file_exists: Whether the file existed before it was read.

    Returns:
        A found or not-found response.
    """
    if found is None:
        return SectionNotFoundResponse(file=str(file_path), file_exists=file_exists, query=query)
    section = found.section
    return SectionFoundResponse(
        file=str(file_path),
        file_exists=file_exists,
        query=query,
        heading=section.heading,
        level=section.level,
        line_start=section.line_start,
        line_end=section.line_end,
        text=found.text,
    )


def build_verify_response(result: IntegrityResult, *, file_exists: bool) -> VerifyResponse:
    """Build the ``docs verify`` response.

    Args:
        result: What :func:`skilllint.vendor_cache.verify_integrity` returned.
        file_exists: Whether the file existed before it was read.

    Returns:
        The response.
    """
    return VerifyResponse(
        status=result.status,
        file=str(result.file_path),
        file_exists=file_exists,
        computed_sha256=result.computed_sha256,
        computed_bytes=result.computed_bytes,
        expected_sha256=result.expected_sha256,
        expected_bytes=result.expected_bytes,
    )


# --- output -----------------------------------------------------------------------------------


def emit_response(response: BaseModel) -> None:
    r"""Write *response* to stdout as one compact JSON line.

    This is the only stdout writer on the ``--json`` path. The line is
    ``model_dump_json()`` plus ``\\n``: no indentation, no extra whitespace, non-ASCII as UTF-8.

    Args:
        response: The response model to print.
    """
    sys.stdout.write(response.model_dump_json() + "\n")
    sys.stdout.flush()
