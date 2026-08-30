"""Guard against provenance-registry.json locators pointing at nothing.

packages/skilllint/schemas/provenance-registry.json asserts that specific
Python symbols back specific rule claims, but nothing loads the registry, so
nothing checks those assertions are true. During #102's review a human found
four locators pointing at symbols that did not exist (see #136). This test
imports every ``python_constant`` locator's module and resolves its symbol,
so drift is caught by CI instead of by a reviewer reading JSON.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "packages" / "skilllint" / "schemas" / "provenance-registry.json"

# docs/design-rule-provenance-registry.md:155 documents assertion_location.source_type
# as "python_constant | schema_json_field | schema_json_enum".
_KNOWN_SOURCE_TYPES = frozenset({"python_constant", "schema_json_field", "schema_json_enum"})


def test_provenance_registry_python_constant_locators_resolve() -> None:
    """Every python_constant assertion_location must import and resolve."""
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for claim_id, claim in registry["claims"].items():
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
        target = importlib.import_module(module_name)
        for part in location["symbol"].split("."):
            assert hasattr(target, part), (
                f"{claim_id}: {recorded_file} has no symbol '{location['symbol']}' (missing '{part}')"
            )
            target = getattr(target, part)
