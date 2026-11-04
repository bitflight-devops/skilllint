"""GitLab Code Quality projection with explicit handling of unsupported findings."""

from __future__ import annotations

import hashlib
import json
import operator
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from skilllint.models import FileResults, ValidationIssue


class GitLabLines(BaseModel):
    """One-based line required by GitLab, including labelled file-level anchors."""

    model_config = ConfigDict(frozen=True)
    begin: int


class GitLabLocation(BaseModel):
    """Repository-relative file and its display line."""

    model_config = ConfigDict(frozen=True)
    path: str
    lines: GitLabLines


class GitLabFinding(BaseModel):
    """The fields consumed by GitLab's Code Quality report parser.

    Contract: https://docs.gitlab.com/ci/testing/code_quality/#code-quality-report-format
    """

    model_config = ConfigDict(frozen=True)
    description: str
    check_name: str
    fingerprint: str
    severity: Literal["major", "minor", "info"]
    location: GitLabLocation


def _repository_root() -> Path:
    """Return the enclosing checkout root, or cwd for an exported source tree."""
    cwd = Path.cwd()
    return next((path for path in (cwd, *cwd.parents) if (path / ".git").exists()), cwd)


def _repository_file(path: Path, root: Path) -> str | None:
    """Return a repository file path, never a directory or external source.

    Preserve in-tree symlink spellings when possible. Resolve parent traversals
    before relativizing, rather than incorrectly cancelling a symlink and '..'.

    Returns:
        A POSIX relative path without './', or None if unrepresentable.
    """
    absolute = path if path.is_absolute() else Path.cwd() / path
    try:
        resolved = absolute.resolve()
        resolved.relative_to(root)
        relative = (resolved if ".." in absolute.parts else absolute).relative_to(root)
        return relative.as_posix() if absolute.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


def _description(issue: ValidationIssue) -> str:
    """Return the full finding text, explicitly labelling unknown positions."""
    description = f"{issue.field}: {issue.message}" if issue.field else issue.message
    source = issue.source_location
    if source is None or source.start is None:
        description = f"[file-level; line 1 is a display anchor, not a source position] {description}"
    if issue.suggestion:
        description += f"\nSuggestion: {issue.suggestion}"
    if issue.docs_url:
        description += f"\nHelp: {issue.docs_url}"
    return description


def _unsupported(target: Path, validator: str, issue: ValidationIssue) -> str:
    """Retain complete unsupported finding details in one safe diagnostic line.

    Returns:
        An escaped diagnostic including every finding field.
    """
    source = issue.source_location
    details = {
        "path": target.as_posix(),
        "validator": validator,
        **issue.model_dump(),
        "source_location": source.model_dump(mode="json") if source is not None else None,
    }
    return (
        "skilllint: GitLab Code Quality omitted a finding with no repository file; "
        "details (use json-lines for a complete report): " + json.dumps(details, ensure_ascii=True, sort_keys=True)
    )


def gitlab_report(file_results: FileResults, *, verbose: bool = False) -> tuple[list[GitLabFinding], list[str]]:
    """Project visible findings, preserving duplicates without fingerprint clashes.

    Fingerprints hash semantic identity and a duplicate occurrence number, not
    absolute checkout paths or coordinates. Sorting occurrences by source
    position makes reordered input stable and distinguishes identical findings.

    Returns:
        Sorted Code Quality findings and diagnostics for every omitted finding.
    """
    root = _repository_root()
    candidates: list[tuple[str, tuple[int, int, str], GitLabFinding]] = []
    diagnostics: list[str] = []
    for target, validator_results in file_results.items():
        for validator, result in validator_results:
            issues = [*result.errors, *result.warnings, *(result.info if verbose else [])]
            for issue in issues:
                source = issue.source_location
                path = _repository_file(source.path if source is not None else target, root)
                if path is None:
                    diagnostics.append(_unsupported(target, validator, issue))
                    continue
                start = source.start if source is not None else None
                finding = GitLabFinding(
                    description=_description(issue),
                    check_name=issue.code,
                    fingerprint="",
                    severity="major"
                    if issue.severity == "error"
                    else "minor"
                    if issue.severity == "warning"
                    else "info",
                    location=GitLabLocation(path=path, lines=GitLabLines(begin=start.line if start else 1)),
                )
                identity = json.dumps([path, validator, issue.code, issue.field, issue.message], ensure_ascii=True)
                order = (
                    start.line if start else 0,
                    start.column if start else 0,
                    json.dumps(finding.model_dump(), ensure_ascii=True, sort_keys=True),
                )
                candidates.append((identity, order, finding))
    occurrences: Counter[str] = Counter()
    findings: list[GitLabFinding] = []
    for identity, _order, finding in sorted(candidates, key=operator.itemgetter(slice(2))):
        occurrence = occurrences[identity]
        occurrences[identity] += 1
        fingerprint = hashlib.sha256(f"{identity}\n{occurrence}".encode()).hexdigest()
        findings.append(finding.model_copy(update={"fingerprint": fingerprint}))
    return findings, sorted(diagnostics)


def emit_gitlab(file_results: FileResults, *, verbose: bool = False) -> None:
    """Write a BOM-free JSON array; disclose unsupported findings on stderr."""
    findings, diagnostics = gitlab_report(file_results, verbose=verbose)
    # ASCII JSON is also BOM-free UTF-8 and safely escapes terminal controls.
    print(json.dumps([finding.model_dump() for finding in findings], ensure_ascii=True, indent=2))
    for diagnostic in diagnostics:
        print(diagnostic, file=sys.stderr)
