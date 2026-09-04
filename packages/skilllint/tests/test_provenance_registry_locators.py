"""Guard against claim files asserting values the code no longer holds.

packages/skilllint/schemas/provenance-registry.json and
packages/skilllint/schemas/opinion-catalog.json each assert that a specific
Python symbol backs a specific rule claim, and (since #146) what value that
symbol currently holds. Nothing loaded either file, so nothing checked those
assertions were true. During #102's review a human found four locators
pointing at symbols that did not exist (see #136); a separate audit for #146
found opinion-catalog.json rows citing stale line numbers and one row
asserting "no vendor document enumerates this set" when the cached vendor
doc does exactly that. This test imports every ``python_constant`` locator's
module, resolves its symbol, and asserts the live value matches
``expected_value``, so both classes of drift are caught by CI instead of by
a reviewer reading JSON.
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from re import Pattern
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCHEMAS_DIR = REPO_ROOT / "packages" / "skilllint" / "schemas"
REGISTRY_PATH = SCHEMAS_DIR / "provenance-registry.json"
OPINION_CATALOG_PATH = SCHEMAS_DIR / "opinion-catalog.json"

# docs/design-rule-provenance-registry.md:155 documents assertion_location.source_type
# as "python_constant | schema_json_field | schema_json_enum".
_KNOWN_SOURCE_TYPES = frozenset({"python_constant", "schema_json_field", "schema_json_enum"})


def _normalize(value: object) -> object:
    """Reduce a resolved symbol or an expected_value to a comparable form.

    Covers every claim shape currently in the two catalogs: scalars, regex
    patterns (compared by .pattern), and sets/lists/tuples of strings
    (compared order-independently, since frozenset iteration order is not
    a claim any rule makes).
    """
    if isinstance(value, Pattern):
        return value.pattern
    if isinstance(value, (set, frozenset, list, tuple)):
        return sorted(str(item) for item in value)
    return value


def _iter_claims() -> list[tuple[str, dict[str, Any]]]:
    """Yield (claim_id, claim) from both catalog files.

    provenance-registry.json claims have a vendor authority; opinion-catalog.json
    rows are explicit "no vendor source" opinions. Both make the same kind of
    locator + value assertion about the code, so both are checked by the same
    loop rather than by two near-duplicate tests.
    """
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    opinions = json.loads(OPINION_CATALOG_PATH.read_text(encoding="utf-8"))
    return [*registry["claims"].items(), *opinions["opinions"].items()]


def test_claim_locators_resolve_and_values_match() -> None:
    """Every python_constant assertion_location must import, resolve, and match."""
    for claim_id, claim in _iter_claims():
        location = claim["assertion_location"]
        source_type = location["source_type"]
        assert source_type in _KNOWN_SOURCE_TYPES, f"{claim_id}: unrecognized source_type '{source_type}'"
        if source_type != "python_constant":
            continue

        recorded_file = location["file"]
        assert (REPO_ROOT / recorded_file).is_file(), (
            f"{claim_id}: assertion_location.file '{recorded_file}' does not exist"
        )

        module_name = recorded_file.removeprefix("packages/").removesuffix(".py").replace("/", ".")
        target: object = importlib.import_module(module_name)
        for part in location["symbol"].split("."):
            assert hasattr(target, part), (
                f"{claim_id}: {recorded_file} has no symbol '{location['symbol']}' (missing '{part}')"
            )
            target = getattr(target, part)

        assert "expected_value" in claim, f"{claim_id}: missing expected_value"
        actual = _normalize(target)
        expected = _normalize(claim["expected_value"])
        assert actual == expected, (
            f"{claim_id}: {recorded_file}.{location['symbol']} is {actual!r}, but expected_value says {expected!r}"
        )


def test_opinion_catalog_references_carry_no_stale_line_numbers() -> None:
    """references entries must not cite a line number.

    A line number is exactly the fact assertion_location.symbol now makes
    machine-checkable. Keeping one in prose lets it rot silently again (see
    #146: 4 of 9 rows already cited wrong numbers before this guard existed).
    """
    opinions = json.loads(OPINION_CATALOG_PATH.read_text(encoding="utf-8"))
    line_number_pattern = re.compile(r"\bline[s]?\s+\d+")
    for claim_id, claim in opinions["opinions"].items():
        for reference in claim.get("references", []):
            assert not line_number_pattern.search(reference), (
                f"{claim_id}: reference cites a line number, which the "
                f"assertion_location field now tracks and this test checks: {reference!r}"
            )
