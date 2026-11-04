"""Tests for reproducible CLI output documentation artifacts."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET

import pytest
from scripts import capture_output_examples as capture

_SHALLOW_WARNING = (
    b'/venv/lib/vcs_versioning/_backends/_git.py:530: UserWarning: "/checkout" is shallow and may cause errors\n'
    b"  pre_parse(wd)\n"
)


def test_svg_is_deterministic_and_labels_visual_wrapping():
    raw = b'{"schema_version":1,"message":"A < B & C","severity":"error"}\n'
    first = capture.render_jsonl(raw)
    assert first == capture.render_jsonl(raw)
    assert all(line == line.rstrip() for line in first.splitlines())
    root = ET.fromstring(first)
    visible = "".join(root.itertext())
    assert "JSONL" in visible
    assert "Visual" in visible
    assert b"&lt;" in first
    assert b"&amp;" in first


@pytest.mark.parametrize(
    "capture_output",
    [
        capture.capture_jsonl,
        capture.capture_concise,
        capture.capture_github,
        capture.capture_gitlab,
        capture.capture_junit,
        capture.capture_full,
    ],
)
def test_capture_preserves_raw_stdout(monkeypatch, capture_output):
    raw = b'{"message":"demo"}\r\n'
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, b"")
    )
    assert capture_output() == raw


@pytest.mark.parametrize(
    "capture_output",
    [
        capture.capture_jsonl,
        capture.capture_concise,
        capture.capture_github,
        capture.capture_gitlab,
        capture.capture_junit,
        capture.capture_full,
    ],
)
def test_capture_pins_child_encoding_without_changing_parent(monkeypatch, capture_output):
    monkeypatch.setenv("PYTHONIOENCODING", "utf-16")
    calls = []

    def run(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 1, b"{}\n", b"")

    monkeypatch.setattr(capture.subprocess, "run", run)
    assert capture_output() == b"{}\n"
    assert calls[0]["env"]["PYTHONIOENCODING"] == "utf-8"
    assert capture.os.environ["PYTHONIOENCODING"] == "utf-16"


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize(
    "capture_output",
    [
        capture.capture_jsonl,
        capture.capture_concise,
        capture.capture_github,
        capture.capture_gitlab,
        capture.capture_junit,
        capture.capture_full,
    ],
)
def test_capture_ignores_only_the_known_shallow_checkout_warning(monkeypatch, newline, capture_output):
    raw = b'{"message":"demo"}\n'
    warning = _SHALLOW_WARNING.replace(b"\n", newline)
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, warning)
    )
    assert capture_output() == raw


@pytest.mark.parametrize(
    "stderr",
    [
        _SHALLOW_WARNING + b"genuine diagnostic\n",
        b"genuine diagnostic\n" + _SHALLOW_WARNING,
        _SHALLOW_WARNING.replace(b"vcs_versioning", b"unrelated_module"),
        _SHALLOW_WARNING.replace(b"pre_parse(wd)", b"different_source()"),
    ],
)
@pytest.mark.parametrize(
    "capture_output",
    [
        capture.capture_jsonl,
        capture.capture_concise,
        capture.capture_github,
        capture.capture_gitlab,
        capture.capture_junit,
        capture.capture_full,
    ],
)
def test_capture_does_not_hide_other_stderr(monkeypatch, stderr, capture_output):
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, b"{}\n", stderr)
    )
    with pytest.raises(RuntimeError):
        capture_output()


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr"), [(0, b"", b""), (2, b"", b"bad usage"), (1, b"", b""), (1, b"{}\n", b"warning")]
)
@pytest.mark.parametrize(
    "capture_output",
    [
        capture.capture_jsonl,
        capture.capture_concise,
        capture.capture_github,
        capture.capture_gitlab,
        capture.capture_junit,
        capture.capture_full,
    ],
)
def test_capture_rejects_unexpected_result(monkeypatch, exit_code, stdout, stderr, capture_output):
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, exit_code, stdout, stderr)
    )
    with pytest.raises(RuntimeError):
        capture_output()


@pytest.mark.parametrize(
    "artifact",
    [
        "json-lines.jsonl",
        "json-lines.svg",
        "concise.txt",
        "concise.svg",
        "github.txt",
        "github.svg",
        "gitlab.json",
        "gitlab.svg",
        "junit.xml",
        "junit.svg",
        "full.ansi",
        "full.svg",
    ],
)
def test_check_detects_drift_without_writing(monkeypatch, tmp_path, artifact):
    raw = b'{"message":"demo"}\n'
    monkeypatch.setattr(capture, "capture_jsonl", lambda: raw)
    monkeypatch.setattr(capture, "capture_concise", lambda: b"demo.md:2:1: error[FM010] name: bad name\n")
    monkeypatch.setattr(capture, "capture_github", lambda: b"::error file=demo.md,line=2,col=1,title=FM010::bad name\n")
    monkeypatch.setattr(capture, "capture_gitlab", lambda: b'[\n  {"description": "bad name"}\n]\n')
    monkeypatch.setattr(capture, "capture_junit", lambda: b'<testsuites><testsuite name="demo" /></testsuites>\n')
    monkeypatch.setattr(capture, "capture_full", lambda: b"\x1b[31merror[FM010]\x1b[0m\n")
    monkeypatch.setattr(capture, "OUTPUT", tmp_path)
    assert capture.main(["--check"]) == 1
    assert not list(tmp_path.iterdir())
    assert capture.main([]) == 0
    assert capture.main(["--check"]) == 0
    path = tmp_path / artifact
    path.write_bytes(b"stale")
    assert capture.main(["--check"]) == 1
    assert path.read_bytes() == b"stale"


@pytest.mark.parametrize(("captured_newline", "checkout_newline"), [(b"\r\n", b"\n"), (b"\n", b"\r\n")])
def test_check_accepts_native_and_checkout_newlines_without_rewriting(
    monkeypatch, tmp_path, captured_newline, checkout_newline
):
    raw = b'{"message":"demo"}' + captured_newline
    concise = b"demo.md:2:1: error[FM010] name: bad name" + captured_newline
    monkeypatch.setattr(capture, "capture_jsonl", lambda: raw)
    github = b"::error file=demo.md,line=2,col=1,title=FM010::bad name" + captured_newline
    monkeypatch.setattr(capture, "capture_concise", lambda: concise)
    monkeypatch.setattr(capture, "capture_github", lambda: github)
    gitlab = b'[ {"description":"demo"} ]' + captured_newline
    monkeypatch.setattr(capture, "capture_gitlab", lambda: gitlab)
    junit = b'<testsuites tests="1"/>' + captured_newline
    monkeypatch.setattr(capture, "capture_junit", lambda: junit)
    monkeypatch.setattr(capture, "capture_full", lambda: b"\x1b[31merror[FM010]\x1b[0m\n")
    monkeypatch.setattr(capture, "OUTPUT", tmp_path)
    assert capture.main([]) == 0
    raw_path = tmp_path / "json-lines.jsonl"
    assert raw_path.read_bytes() == raw
    assert (tmp_path / "concise.txt").read_bytes() == concise
    paths = [
        tmp_path / name
        for name in (
            "json-lines.jsonl",
            "json-lines.svg",
            "concise.txt",
            "concise.svg",
            "github.txt",
            "github.svg",
            "gitlab.json",
            "gitlab.svg",
            "junit.xml",
            "junit.svg",
            "full.ansi",
            "full.svg",
        )
    ]
    for path in paths:
        path.write_bytes(capture.canonical_line_endings(path.read_bytes()).replace(b"\n", checkout_newline))
    before = {path: path.read_bytes() for path in paths}
    assert capture.main(["--check"]) == 0
    assert {path: path.read_bytes() for path in before} == before
    assert capture.render_jsonl(raw) == capture.render_jsonl(capture.canonical_line_endings(raw))
    assert capture.render_concise(concise) == capture.render_concise(capture.canonical_line_endings(concise))
    assert (tmp_path / "github.txt").read_bytes() == capture.canonical_line_endings(github).replace(
        b"\n", checkout_newline
    )
    assert capture.render_github(github) == capture.render_github(capture.canonical_line_endings(github))
    assert (tmp_path / "gitlab.json").read_bytes() == capture.canonical_line_endings(gitlab).replace(
        b"\n", checkout_newline
    )
    assert capture.render_gitlab(gitlab) == capture.render_gitlab(capture.canonical_line_endings(gitlab))
    assert (tmp_path / "junit.xml").read_bytes() == capture.canonical_line_endings(junit).replace(
        b"\n", checkout_newline
    )
    assert capture.render_junit(junit) == capture.render_junit(capture.canonical_line_endings(junit))
    raw_path.write_bytes(b'{"message":"changed"}\n')
    assert capture.main(["--check"]) == 1


def test_newline_normalization_preserves_escaped_content_and_standalone_cr():
    data = b'{"message":"literal \\r\\n"}\r\nstandalone\r'
    assert capture.canonical_line_endings(data) == b'{"message":"literal \\r\\n"}\nstandalone\r'


def test_committed_examples_match_real_cli_twice():
    first = capture.capture_jsonl()
    assert first == capture.capture_jsonl()
    assert first.endswith(b"\n")
    records = [json.loads(line) for line in first.splitlines()]
    assert records
    assert all(record["schema_version"] == 1 for record in records)
    assert capture.canonical_line_endings((capture.OUTPUT / "json-lines.jsonl").read_bytes()) == (
        capture.canonical_line_endings(first)
    )
    assert capture.canonical_line_endings((capture.OUTPUT / "json-lines.svg").read_bytes()) == (
        capture.canonical_line_endings(capture.render_jsonl(first))
    )


def test_concise_svg_preserves_literal_monochrome_findings():
    raw = b"demo.md:2:1: error[FM010] name: A < B & [red]C[/red] :warning:\n"
    first = capture.render_concise(raw)
    assert first == capture.render_concise(raw)
    assert all(line == line.rstrip() for line in first.splitlines())
    root = ET.fromstring(first)
    visible = "".join(root.itertext()).replace("\N{NO-BREAK SPACE}", " ")
    assert "Concise actual-output preview" in visible
    assert "Visual wrapping only; raw output has one finding per line." in visible
    assert raw.decode().strip() in visible
    assert b"&lt;" in first
    assert b"&amp;" in first
    findings = [node for node in root.iter("{http://www.w3.org/2000/svg}text") if "error[FM010]" in (node.text or "")]
    assert len(findings) == 1
    assert not list(findings[0])  # No syntax-coloured subspans in the diagnostic.
    clip_ids = {node.attrib["id"] for node in root.iter("{http://www.w3.org/2000/svg}clipPath")}
    for node in root.iter("{http://www.w3.org/2000/svg}text"):
        if "clip-path" in node.attrib and (node.text or "").strip():
            assert node.attrib["clip-path"][5:-1] in clip_ids


def test_concise_command_requests_no_color():
    assert capture.CONCISE_COMMAND == (
        "uv",
        "run",
        "skilllint",
        "check",
        "--platform",
        "claude-code",
        "--output-format",
        "concise",
        "--no-color",
        "examples/output/fixtures/demo-skill/SKILL.md",
    )


def test_committed_concise_examples_match_real_cli_twice():
    first = capture.capture_concise()
    assert first == capture.capture_concise()
    assert first.endswith(b"\n")
    assert len(first.splitlines()) == 1
    assert b"examples/output/fixtures/demo-skill/SKILL.md:2:1: error[FM010] name:" in first
    assert b"\x1b" not in first
    assert capture.canonical_line_endings((capture.OUTPUT / "concise.txt").read_bytes()) == (
        capture.canonical_line_endings(first)
    )
    assert capture.canonical_line_endings((capture.OUTPUT / "concise.svg").read_bytes()) == (
        capture.canonical_line_endings(capture.render_concise(first))
    )


def test_github_svg_is_labelled_as_commands_not_platform_screenshot():
    raw = b"::error file=demo.md,title=FM010::A < B & [red]C[/red] :warning:\n"
    first = capture.render_github(raw)
    assert first == capture.render_github(raw)
    assert all(line == line.rstrip() for line in first.splitlines())
    root = ET.fromstring(first)
    visible = "".join(root.itertext()).replace("\N{NO-BREAK SPACE}", " ")
    assert "GitHub workflow-command preview" in visible
    assert "not a GitHub UI screenshot" in visible
    assert raw.decode().strip() in visible
    clip_ids = {node.attrib["id"] for node in root.iter("{http://www.w3.org/2000/svg}clipPath")}
    for node in root.iter("{http://www.w3.org/2000/svg}text"):
        if "clip-path" in node.attrib and (node.text or "").strip():
            assert node.attrib["clip-path"][5:-1] in clip_ids


def test_committed_github_examples_match_real_cli_twice():
    first = capture.capture_github()
    assert first == capture.capture_github()
    assert first.endswith(b"\n")
    assert len(first.splitlines()) == 1
    assert first.startswith(b"::error file=examples/output/fixtures/demo-skill/SKILL.md,line=2,col=1")
    assert b"\x1b" not in first
    assert capture.canonical_line_endings((capture.OUTPUT / "github.txt").read_bytes()) == (
        capture.canonical_line_endings(first)
    )
    assert capture.canonical_line_endings((capture.OUTPUT / "github.svg").read_bytes()) == (
        capture.canonical_line_endings(capture.render_github(first))
    )


def test_gitlab_preview_and_raw_report_match_real_cli_twice():
    raw = capture.capture_gitlab()
    assert raw == capture.capture_gitlab()
    findings = json.loads(raw)
    assert len(findings) == 1
    assert findings[0]["check_name"] == "FM010"
    assert findings[0]["location"] == {"path": "examples/output/fixtures/demo-skill/SKILL.md", "lines": {"begin": 2}}
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\x1b" not in raw
    svg = capture.render_gitlab(raw)
    assert svg == capture.render_gitlab(raw)
    root = ET.fromstring(svg)
    visible = "".join(root.itertext()).replace("\N{NO-BREAK SPACE}", " ")
    assert "GitLab Code Quality report preview" in visible
    assert "not a GitLab UI screenshot" in visible
    assert "Visual wrapping only" in visible
    assert findings[0]["fingerprint"] in visible
    assert capture.canonical_line_endings(
        (capture.OUTPUT / "gitlab.json").read_bytes()
    ) == capture.canonical_line_endings(raw)
    assert capture.canonical_line_endings(
        (capture.OUTPUT / "gitlab.svg").read_bytes()
    ) == capture.canonical_line_endings(svg)


def test_junit_preview_and_raw_report_match_real_cli_twice():
    raw = capture.capture_junit()
    assert raw == capture.capture_junit()
    report = ET.fromstring(raw)
    assert report.attrib["tests"] == "1"
    assert report.attrib["failures"] == "1"
    assert report.find(".//failure") is not None
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\x1b" not in raw
    svg = capture.render_junit(raw)
    assert svg == capture.render_junit(raw)
    root = ET.fromstring(svg)
    visible = "".join(root.itertext()).replace("\N{NO-BREAK SPACE}", " ")
    assert "JUnit-style XML report preview" in visible
    assert "not a CI UI screenshot" in visible
    assert "Visual wrapping only" in visible
    assert "error[FM010]" in visible
    assert capture.canonical_line_endings(
        (capture.OUTPUT / "junit.xml").read_bytes()
    ) == capture.canonical_line_endings(raw)
    assert capture.canonical_line_endings(
        (capture.OUTPUT / "junit.svg").read_bytes()
    ) == capture.canonical_line_endings(svg)


def test_full_capture_replays_real_colours_and_matches_twice():
    raw = capture.capture_full()
    assert raw == capture.capture_full()
    assert b"\x1b[" in raw
    assert b"error[FM010]" in raw
    assert b"name: Bad Name" in raw
    assert b"^^^^" in raw
    svg = capture.render_full(raw)
    assert svg == capture.render_full(raw)
    visible = "".join(ET.fromstring(svg).itertext()).replace("\N{NO-BREAK SPACE}", " ")
    assert "error[FM010]" in visible
    assert "help:" in visible
    assert "docs:" in visible
    root = ET.fromstring(svg)
    ids = {node.attrib["id"] for node in root.iter() if "id" in node.attrib}
    for node in root.iter("{http://www.w3.org/2000/svg}text"):
        clip = node.attrib.get("clip-path")
        if clip and (node.text or "").strip():
            assert clip[5:-1] in ids
    assert capture.canonical_line_endings(
        (capture.OUTPUT / "full.ansi").read_bytes()
    ) == capture.canonical_line_endings(raw)
    assert capture.canonical_line_endings((capture.OUTPUT / "full.svg").read_bytes()) == capture.canonical_line_endings(
        svg
    )
