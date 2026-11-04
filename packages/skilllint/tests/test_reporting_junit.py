"""JUnit XML parsing, supported consumer fields, identity and result semantics."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import pytest
from hypothesis import given, strategies as st

from skilllint.models import FileResults, ValidationIssue, ValidationResult
from skilllint.reporting_junit import emit_junit, junit_report
from skilllint.source_location import SourceLocation, SourcePosition


def _issue(**updates: object) -> ValidationIssue:
    return ValidationIssue.model_validate({
        "field": "name",
        "severity": "error",
        "message": "bad",
        "code": "FM010",
        **updates,
    })


def _result(*issues: ValidationIssue, passed: bool = False) -> ValidationResult:
    return ValidationResult(
        passed=passed,
        errors=[issue for issue in issues if issue.severity == "error"],
        warnings=[issue for issue in issues if issue.severity == "warning"],
        info=[issue for issue in issues if issue.severity == "info"],
    )


def _results(result: ValidationResult, path: Path = Path("SKILL.md"), validator: str = "Example") -> FileResults:
    return {path: [(validator, result)]}


def test_gitlab_consumer_fields_and_counters():
    # GitLab's published subset reads classname/name, failure body, and testcase
    # system-out. It ignores suite counters and testcase line/status attributes.
    # https://docs.gitlab.com/ci/testing/unit_test_reports/#junit-xml-format-specification
    results = {
        Path("a.md"): [("one", _result(_issue(), _issue(severity="warning")))],
        Path("b.md"): [("two", _result(_issue(severity="warning"), passed=True))],
        Path("c.md"): [("three", _result(passed=True))],
    }
    xml = junit_report(results)
    root = ET.fromstring(xml)
    suite = root.find("testsuite")
    assert suite is not None
    for element in (root, suite):
        assert element.attrib == {"name": "skilllint", "tests": "3", "failures": "1", "errors": "0", "skipped": "0"}
    cases = suite.findall("testcase")
    assert len(cases) == 3
    assert [(case.attrib["classname"], case.attrib["name"]) for case in cases] == [
        ("a.md", "one [1]"),
        ("b.md", "two [1]"),
        ("c.md", "three [1]"),
    ]
    assert "error[FM010]" in cases[0].findtext("failure", "")
    assert "warning[FM010]" in cases[0].findtext("system-out", "")
    assert cases[1].find("failure") is None
    assert "warning[FM010]" in cases[1].findtext("system-out", "")
    assert len(cases[2]) == 0
    assert not root.findall(".//error")
    assert not root.findall(".//skipped")
    # Parse using a second standard XML interface, not string matching alone.
    document = minidom.parseString(xml)
    assert len(document.getElementsByTagName("testcase")) == 3


def test_clean_and_empty_scans_do_not_invent_rule_execution(capsys):
    emit_junit({})
    captured = capsys.readouterr()
    assert captured.err == ""
    root = ET.fromstring(captured.out)
    assert root.attrib["tests"] == "0"
    assert root.findall(".//testcase") == []
    clean = ET.fromstring(junit_report(_results(_result(passed=True))))
    assert clean.attrib["tests"] == "1"
    assert clean.attrib["failures"] == "0"
    assert len(clean.findall(".//testcase")) == 1


@pytest.mark.parametrize("passed", [True, False])
def test_passed_flag_is_authoritative_even_with_inconsistent_findings(passed):
    result = _result(*([_issue()] if passed else []), passed=passed)
    root = ET.fromstring(junit_report(_results(result)))
    assert root.attrib["failures"] == ("0" if passed else "1")
    if passed:
        assert root.find(".//failure") is None
        assert "error[FM010]" in root.findtext(".//system-out", "")
    else:
        assert root.findtext(".//failure") == "Validator reported failure without an error diagnostic."


def test_info_visibility_never_changes_counters_or_identity():
    results = _results(_result(_issue(severity="info"), passed=True))
    quiet = ET.fromstring(junit_report(results))
    verbose = ET.fromstring(junit_report(results, verbose=True))
    assert quiet.attrib == verbose.attrib
    assert quiet.find(".//system-out") is None
    assert "info[FM010]" in verbose.findtext(".//system-out", "")
    assert [case.attrib for case in quiet.findall(".//testcase")] == [
        case.attrib for case in verbose.findall(".//testcase")
    ]


def test_real_source_range_and_complete_help_without_legacy_guessing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    issue = _issue(
        source_location=SourceLocation(
            path=tmp_path / "source.md", start=SourcePosition(line=2, column=3), end=SourcePosition(line=4, column=5)
        ),
        line=99,
        suggestion="Try <this> & that",
        docs_url="https://example.test/?a=1&b=2",
    )
    root = ET.fromstring(junit_report(_results(_result(issue), path=tmp_path)))
    case = root.find(".//testcase")
    assert case is not None
    assert case.attrib["classname"] == "."
    text = root.findtext(".//failure", "")
    assert text.startswith("source.md:2:3-4:5: error[FM010] name: bad")
    assert "Try <this> & that" in text
    assert "https://example.test/?a=1&b=2" in text
    unlocated = ET.fromstring(junit_report(_results(_result(_issue(line=99)))))
    assert unlocated.findtext(".//failure", "").startswith("SKILL.md: error[FM010]")
    assert ":99" not in unlocated.findtext(".//failure", "")


def test_external_missing_and_directory_targets_are_retained(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    results = {
        path: [("test", _result(_issue()))] for path in (tmp_path, tmp_path.parent / "external.md", Path("missing.md"))
    }
    root = ET.fromstring(junit_report(results))
    assert root.attrib["tests"] == "3"
    assert root.attrib["failures"] == "3"
    assert {case.attrib["classname"] for case in root.findall(".//testcase")} == {
        ".",
        str(tmp_path.parent / "external.md"),
        "missing.md",
    }


def test_order_independent_and_duplicate_identities_stay_unique(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    one, two = _result(_issue(message="a")), _result(_issue(message="b"))
    results = {
        Path("a.md"): [("same", one), ("same", two), ("same", one), ("same [2]", one)],
        tmp_path / "a.md": [("same", two)],
        Path("b.md"): [("test\x00", one), (r"test\x00", one)],
    }
    reverse = {path: list(reversed(entries)) for path, entries in reversed(list(results.items()))}
    raw = junit_report(results)
    assert raw == junit_report(reverse)
    root = ET.fromstring(raw)
    identities = [(case.attrib["classname"], case.attrib["name"]) for case in root.findall(".//testcase")]
    assert len(identities) == len(set(identities)) == 7


def test_xml_special_characters_controls_surrogates_and_carriage_returns():
    value = '<tag attr="x">&\r\n\t\x00\x1b\ud800\ufffe\uffff\U0001f40d'
    root = ET.fromstring(junit_report(_results(_result(_issue(message=value)), validator=value)))
    expected = '<tag attr="x">&\r\n\t\\x00\\x1b\\ud800\\ufffe\\uffff\U0001f40d'
    assert expected in root.findtext(".//failure", "")
    case = root.find(".//testcase")
    assert case is not None
    assert case.attrib["name"] == expected + " [1]"


@given(st.text())
def test_arbitrary_unicode_is_well_formed_and_valid_text_round_trips(value):
    raw = junit_report(_results(_result(_issue(message=value, field="")), validator=value))
    root = ET.fromstring(raw.encode("utf-8"))
    assert root.attrib["failures"] == "1"
    assert "\x1b" not in raw
    # Hypothesis's default text alphabet excludes surrogates; XML-prohibited
    # codepoints below U+0020 and FFFE/FFFF are tested separately above.
    if all(c in "\t\n\r" or " " <= c <= "\ud7ff" or "\ue000" <= c <= "\ufffd" or c >= "\U00010000" for c in value):
        assert root.findtext(".//failure") == "SKILL.md: error[FM010] " + value


def test_stdout_encoding_cannot_contradict_xml_declaration(monkeypatch):
    output = io.BytesIO()
    stream = io.TextIOWrapper(output, encoding="ascii")
    monkeypatch.setattr("sys.stdout", stream)
    emit_junit(_results(_result(_issue(message="café 🐍"))))
    stream.flush()
    raw = output.getvalue()
    assert raw.isascii()
    assert "café 🐍" in ET.fromstring(raw).findtext(".//failure", "")
