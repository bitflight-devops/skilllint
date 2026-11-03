"""Tests for reproducible CLI output documentation artifacts."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET

import pytest
from scripts import capture_output_examples as capture


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


@pytest.mark.parametrize("capture_output", [capture.capture_jsonl, capture.capture_concise])
def test_capture_preserves_raw_stdout(monkeypatch, capture_output):
    raw = b'{"message":"demo"}\n'
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, b"")
    )
    assert capture_output() == raw


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr"), [(0, b"", b""), (2, b"", b"bad usage"), (1, b"", b""), (1, b"{}\n", b"warning")]
)
@pytest.mark.parametrize("capture_output", [capture.capture_jsonl, capture.capture_concise])
def test_capture_rejects_unexpected_result(monkeypatch, exit_code, stdout, stderr, capture_output):
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, exit_code, stdout, stderr)
    )
    with pytest.raises(RuntimeError):
        capture_output()


@pytest.mark.parametrize("artifact", ["json-lines.jsonl", "json-lines.svg", "concise.txt", "concise.svg"])
def test_check_detects_drift_without_writing(monkeypatch, tmp_path, artifact):
    raw = b'{"message":"demo"}\n'
    monkeypatch.setattr(capture, "capture_jsonl", lambda: raw)
    monkeypatch.setattr(capture, "capture_concise", lambda: b"demo.md:2:1: error[FM010] name: bad name\n")
    monkeypatch.setattr(capture, "OUTPUT", tmp_path)
    assert capture.main(["--check"]) == 1
    assert not list(tmp_path.iterdir())
    assert capture.main([]) == 0
    assert capture.main(["--check"]) == 0
    path = tmp_path / artifact
    path.write_bytes(b"stale")
    assert capture.main(["--check"]) == 1
    assert path.read_bytes() == b"stale"


def test_committed_examples_match_real_cli_twice():
    first = capture.capture_jsonl()
    assert first == capture.capture_jsonl()
    assert first.endswith(b"\n")
    records = [json.loads(line) for line in first.splitlines()]
    assert records
    assert all(record["schema_version"] == 1 for record in records)
    assert (capture.OUTPUT / "json-lines.jsonl").read_bytes() == first
    assert (capture.OUTPUT / "json-lines.svg").read_bytes() == capture.render_jsonl(first)


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
    assert (capture.OUTPUT / "concise.txt").read_bytes() == first
    assert (capture.OUTPUT / "concise.svg").read_bytes() == capture.render_concise(first)
