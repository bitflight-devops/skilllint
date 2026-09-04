#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "skilllint",
# ]
#
# [tool.uv.sources]
# skilllint = { path = ".." }
# ///
"""L3 drift check: re-extract vendor-backed provenance claims and diff them.

Implements Stage 4 ("Compare") of docs/design-rule-provenance-registry.md for
the two claims that currently have a real vendor authority document
(HK002.valid_event_types, HK003.valid_hook_types) -- both cite
code.claude.com/docs/en/hooks.md, cached under .claude/vendor/sources/.

Extraction (design doc Stage 3) is mechanical, not LLM-driven: HK002 scrapes
level-3 headings under the "Hook events" section, HK003 splits the "Common
fields" table's `type` row. Add a claim here only when its extraction is this
simple -- LLM-based extraction (the design doc's Stage 3) is deferred until a
claim actually needs prose interpretation.

Usage::

    uv run --script scripts/refresh_claim_values.py

If a claim's live-extracted value differs from provenance-registry.json's
recorded ``expected_value``, this rewrites ``expected_value`` and
``x-audited`` in place and exits 1 (signalling "changed" to the caller, e.g.
so a CI workflow can open a PR). Exits 0 when nothing changed.

Exit codes:
    0 -- no drift; every checked claim's expected_value already matches
    1 -- drift found and written to provenance-registry.json
    2 -- a claim's vendor document could not be fetched and no cache exists
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from skilllint.vendor_cache import CacheStatus, NoCacheError, fetch_or_cached, read_section

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = REPO_ROOT / "packages" / "skilllint" / "schemas" / "provenance-registry.json"


def _extract_hk002(section_text: str) -> list[str]:
    """Extract HK002's event names from the "Hook events" section's level-3 headings.

    Returns:
        Sorted event type names.
    """
    return sorted(re.findall(r"^### (\S+)", section_text, re.MULTILINE))


def _extract_hk003(section_text: str) -> list[str]:
    """Extract HK003's hook types from the "Common fields" table's `type` row.

    Returns:
        Sorted hook type values, or an empty list if the `type` row isn't found.
    """
    for line in section_text.splitlines():
        if line.strip().startswith("| `type`"):
            return sorted(re.findall(r'`"(\w+)"`', line))
    return []


# Claims this script knows how to re-extract. Each maps a claim ID to the
# heading its value lives under and the function that pulls values out of
# that section's text. A claim not listed here is skipped, not failed --
# most claims cite an in-repo tracked schema file (checked by ty/pytest on
# every commit already), not a vendor cache entry this script needs to fetch.
_KNOWN_EXTRACTORS: dict[str, tuple[str, Callable[[str], list[str]]]] = {
    "HK002.valid_event_types": ("Hook events", _extract_hk002),
    "HK003.valid_hook_types": ("Common fields", _extract_hk003),
}


def _refresh_one(claim_id: str, claim: dict) -> bool:
    """Re-fetch and re-extract one claim; rewrite it in place if the value changed.

    Returns:
        True if the claim's expected_value was rewritten.
    """
    heading, extractor = _KNOWN_EXTRACTORS[claim_id]
    authority_url = claim["authority"]["authority_url"]

    try:
        result = fetch_or_cached(authority_url, force=True)
    except NoCacheError as exc:
        print(f"ERROR: {claim_id}: cannot fetch {exc.url} and no cache exists ({exc.reason})", file=sys.stderr)
        sys.exit(2)

    if result.status is CacheStatus.STALE:
        print(f"WARNING: {claim_id}: network fetch failed, serving stale cache at {result.path}", file=sys.stderr)

    section_text = read_section(result.path, heading)
    if section_text is None:
        print(f"ERROR: {claim_id}: heading '{heading}' not found in {result.path}", file=sys.stderr)
        sys.exit(2)

    extracted = extractor(section_text)
    current = sorted(claim["expected_value"])

    if extracted == current:
        print(f"OK: {claim_id}: unchanged ({len(extracted)} values)")
        return False

    print(f"DRIFT: {claim_id}: {sorted(set(current) - set(extracted))=} {sorted(set(extracted) - set(current))=}")
    claim["expected_value"] = extracted
    claim["x-audited"] = {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "source": str(result.path.relative_to(REPO_ROOT)),
    }
    return True


def main() -> int:
    """Re-extract every known claim and rewrite the registry if any drifted.

    Returns:
        0 if nothing changed, 1 if drift was found and written.
    """
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    changed = False
    for claim_id, claim in registry["claims"].items():
        if claim_id not in _KNOWN_EXTRACTORS:
            continue
        changed = _refresh_one(claim_id, claim) or changed

    if changed:
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote drift to {REGISTRY_PATH}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
