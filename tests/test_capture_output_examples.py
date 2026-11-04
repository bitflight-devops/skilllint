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


def test_capture_preserves_raw_stdout(monkeypatch):
    raw = b'{"message":"demo"}\r\n'
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, b"")
    )
    assert capture.capture_jsonl() == raw


def test_capture_pins_child_encoding_without_changing_parent(monkeypatch):
    monkeypatch.setenv("PYTHONIOENCODING", "utf-16")
    calls = []

    def run(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 1, b"{}\n", b"")

    monkeypatch.setattr(capture.subprocess, "run", run)
    assert capture.capture_jsonl() == b"{}\n"
    assert calls[0]["env"]["PYTHONIOENCODING"] == "utf-8"
    assert capture.os.environ["PYTHONIOENCODING"] == "utf-16"


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_capture_ignores_only_the_known_shallow_checkout_warning(monkeypatch, newline):
    raw = b'{"message":"demo"}\n'
    warning = _SHALLOW_WARNING.replace(b"\n", newline)
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, raw, warning)
    )
    assert capture.capture_jsonl() == raw


@pytest.mark.parametrize(
    "stderr",
    [
        _SHALLOW_WARNING + b"genuine diagnostic\n",
        b"genuine diagnostic\n" + _SHALLOW_WARNING,
        _SHALLOW_WARNING.replace(b"vcs_versioning", b"unrelated_module"),
        _SHALLOW_WARNING.replace(b"pre_parse(wd)", b"different_source()"),
    ],
)
def test_capture_does_not_hide_other_stderr(monkeypatch, stderr):
    monkeypatch.setattr(
        capture.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, b"{}\n", stderr)
    )
    with pytest.raises(RuntimeError):
        capture.capture_jsonl()


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


def test_check_accepts_native_and_checkout_newlines_without_rewriting(monkeypatch, tmp_path):
    raw = b'{"message":"demo"}\r\n'
    monkeypatch.setattr(capture, "capture_jsonl", lambda: raw)
    monkeypatch.setattr(capture, "OUTPUT", tmp_path)
    assert capture.main([]) == 0
    raw_path = tmp_path / "json-lines.jsonl"
    svg_path = tmp_path / "json-lines.svg"
    assert raw_path.read_bytes() == raw
    raw_path.write_bytes(raw.replace(b"\r\n", b"\n"))
    svg_path.write_bytes(svg_path.read_bytes().replace(b"\n", b"\r\n"))
    before = {path: path.read_bytes() for path in (raw_path, svg_path)}
    assert capture.main(["--check"]) == 0
    assert {path: path.read_bytes() for path in before} == before
    assert capture.render_jsonl(raw) == capture.render_jsonl(raw.replace(b"\r\n", b"\n"))
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
