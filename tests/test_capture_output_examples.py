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


def test_capture_preserves_raw_stdout(monkeypatch):
    raw = b'{"message":"demo"}\n'
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, b"")
    )
    assert capture.capture_jsonl() == raw


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr"), [(0, b"", b""), (2, b"", b"bad usage"), (1, b"", b""), (1, b"{}\n", b"warning")]
)
def test_capture_rejects_unexpected_result(monkeypatch, exit_code, stdout, stderr):
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, exit_code, stdout, stderr)
    )
    with pytest.raises(RuntimeError):
        capture.capture_jsonl()


def test_check_detects_drift_without_writing(monkeypatch, tmp_path):
    raw = b'{"message":"demo"}\n'
    monkeypatch.setattr(capture, "capture_jsonl", lambda: raw)
    monkeypatch.setattr(capture, "OUTPUT", tmp_path)
    assert capture.main(["--check"]) == 1
    assert not list(tmp_path.iterdir())
    assert capture.main([]) == 0
    assert capture.main(["--check"]) == 0
    path = tmp_path / "json-lines.jsonl"
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
