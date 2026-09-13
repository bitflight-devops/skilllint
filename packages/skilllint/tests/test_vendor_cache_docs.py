from __future__ import annotations

import re
from pathlib import Path

GUIDE = Path(__file__).parents[3] / "docs" / "vendor-cache.md"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def test_canonical_guide_and_commands_are_present() -> None:
    text = _guide()
    assert text.startswith("# Vendor documentation cache\n")
    for command in ("fetch", "fetch-authorities", "latest", "sections", "section", "verify"):
        assert f"skilllint docs {command}" in text
    assert "scripts/fetch_doc_source.py" in text
    assert "--force" in text
    assert "--ttl 0" in text


def test_recipes_are_source_coupled_to_public_implementation() -> None:
    text = _guide()
    source = (Path(__file__).parents[1] / "vendor_cache.py").read_text(encoding="utf-8")
    cli = (Path(__file__).parents[1] / "cli_docs.py").read_text(encoding="utf-8")
    script = (GUIDE.parents[1] / "scripts" / "fetch_doc_source.py").read_text(encoding="utf-8")
    for status in ("NEW", "FRESH", "UNCHANGED", "REFRESHED", "STALE"):
        assert status in text
        assert status in source
    for symbol in ("fetch_or_cached", "find_latest", "format_section_index", "read_section", "verify_integrity"):
        assert symbol in cli
        assert symbol in script
    assert re.search(r"uv run --script scripts/fetch_doc_source\.py fetch", text)


def test_source_first_policy_has_network_sentinel_contract() -> None:
    text = _guide()
    assert ".claude/vendor/{provider}/" in text
    assert "no URL request" in text
    assert "does not select clone content automatically" in text
    assert "fetch-authorities` command is likewise an on-demand URL operation" in text


def test_adversarial_cache_outcomes_are_documented() -> None:
    text = _guide()
    for phrase in (
        "missing or partial pairs",
        "malformed, or incomplete metadata",
        "fenced",
        "No Cache\nAvailable",
        "empty successful HTTP response",
        "decoded response text encoded as\nUTF-8",
    ):
        assert phrase in text
