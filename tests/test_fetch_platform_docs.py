"""Tests for drift detection data model and hash helpers in fetch_platform_docs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from scripts.fetch_platform_docs import (
    DriftReport,
    _read_text_or_none,
    _sha256,
)


def test_sha256_returns_hex_digest() -> None:
    # known SHA-256 of "hello"
    assert (
        _sha256("hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_sha256_same_input_same_output() -> None:
    assert _sha256("foo") == _sha256("foo")


def test_sha256_different_inputs_different_output() -> None:
    assert _sha256("foo") != _sha256("bar")


def test_read_text_or_none_existing_file_returns_content(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    assert _read_text_or_none(f) == "hello"


def test_read_text_or_none_missing_file_returns_none(tmp_path: Path) -> None:
    assert _read_text_or_none(tmp_path / "nonexistent.txt") is None


def test_drift_report_serializable() -> None:
    report = DriftReport(fetch_time="2026-03-11T00:00:00+00:00", changed=[])
    # Must be serializable to JSON via dataclasses.asdict
    d = asdict(report)
    s = json.dumps(d)
    assert "fetch_time" in s
