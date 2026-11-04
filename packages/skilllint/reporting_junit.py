"""JUnit-style XML for executed validation results, not xUnit.net XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # noqa: S405 - serialization only; no XML is parsed.
from collections import Counter
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skilllint.models import FileResults, ValidationIssue


def _xml_text(value: str) -> str:
    """Preserve XML 1.0 text, showing prohibited characters as Python escapes.

    XML entities alone cannot represent prohibited codepoints. Character ranges
    follow https://www.w3.org/TR/xml/#charsets, including lone surrogates.

    Returns:
        Text safe for an XML serializer; markup is escaped by ElementTree.
    """
    return "".join(
        character
        if character in "\t\n\r"
        or "\x20" <= character <= "\ud7ff"
        or "\ue000" <= character <= "\ufffd"
        or "\U00010000" <= character <= "\U0010ffff"
        else ascii(character)[1:-1]
        for character in value
    )


def _path_text(path: Path) -> str:
    """Return a cwd-relative path when possible, retaining external targets."""
    with suppress(ValueError):
        path = path.relative_to(Path.cwd())
    return path.as_posix()


def _issue_text(target: Path, issue: ValidationIssue) -> str:
    """Return complete diagnostic text with only genuine source coordinates."""
    source = issue.source_location
    location = _path_text(source.path if source is not None else target)
    if source is not None and source.start is not None:
        location += f":{source.start.line}:{source.start.column}"
        if source.end is not None:
            location += f"-{source.end.line}:{source.end.column}"
    field = f"{issue.field}: " if issue.field else ""
    text = f"{location}: {issue.severity}[{issue.code}] {field}{issue.message}"
    if issue.suggestion:
        text += f"\nSuggestion: {issue.suggestion}"
    if issue.docs_url:
        text += f"\nHelp: {issue.docs_url}"
    return text


def junit_report(file_results: FileResults, *, verbose: bool = False) -> str:
    """Serialize one testcase per executed target/validator result.

    Failure state follows ValidationResult.passed, exactly as CLI exit status
    does. Warnings and verbose info are testcase output, never failed tests.
    No rule inventory, elapsed time, or unexecuted checks are fabricated.

    Returns:
        Deterministic XML with unique testcase identities and exact counters.
    """
    cases: list[tuple[str, str, bool, str, str]] = []
    for target, validator_results in file_results.items():
        for validator, result in validator_results:
            errors = "\n\n".join(sorted(_issue_text(target, issue) for issue in result.errors))
            output = "\n\n".join(
                sorted(
                    _issue_text(target, issue)
                    for issue in [
                        *result.warnings,
                        *(result.info if verbose else []),
                        *(result.errors if result.passed else []),
                    ]
                )
            )
            cases.append((_path_text(target), validator, result.passed, errors, output))
    counters = {
        "tests": str(len(cases)),
        "failures": str(sum(not passed for _, _, passed, _, _ in cases)),
        "errors": "0",
        "skipped": "0",
    }
    root = ET.Element("testsuites", {"name": "skilllint", **counters})
    suite = ET.SubElement(root, "testsuite", {"name": "skilllint", **counters})
    occurrences: Counter[tuple[str, str]] = Counter()
    for path, validator, passed, errors, output in sorted(cases):
        classname = _xml_text(path)
        name = _xml_text(validator)
        # Count emitted identities, so sanitization and equivalent path aliases
        # cannot create duplicates. Always suffix to avoid a literal "name [2]"
        # colliding with the second occurrence of "name".
        occurrences[classname, name] += 1
        case = ET.SubElement(suite, "testcase", classname=classname, name=f"{name} [{occurrences[classname, name]}]")
        if not passed:
            failure = ET.SubElement(case, "failure", message="Validation failed", type="skilllint.validation")
            failure.text = _xml_text(errors or "Validator reported failure without an error diagnostic.")
        if output:
            ET.SubElement(case, "system-out").text = _xml_text(output)
    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="unicode", xml_declaration=True).replace("\r", "&#13;")
    # ASCII character references keep the declared UTF-8 document valid even
    # when stdout uses a different ASCII-compatible encoding.
    return xml.encode("ascii", "xmlcharrefreplace").decode("ascii")


def emit_junit(file_results: FileResults, *, verbose: bool = False) -> None:
    """Write only the JUnit-style XML report and a final newline to stdout."""
    print(junit_report(file_results, verbose=verbose))
