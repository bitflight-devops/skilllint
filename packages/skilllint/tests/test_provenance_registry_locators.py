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


def test_provenance_registry_python_constant_locators_resolve() -> None:
    """Every python_constant assertion_location must import and resolve."""
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for claim_id, claim in registry["claims"].items():
        location = claim["assertion_location"]
        if location["source_type"] != "python_constant":
            continue
        module_name = location["file"].removeprefix("packages/").removesuffix(".py").replace("/", ".")
        target = importlib.import_module(module_name)
        for part in location["symbol"].split("."):
            assert hasattr(target, part), (
                f"{claim_id}: {location['file']} has no symbol '{location['symbol']}' (missing '{part}')"
            )
            target = getattr(target, part)
