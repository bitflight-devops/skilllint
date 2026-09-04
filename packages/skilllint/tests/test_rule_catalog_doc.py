"""Guard rule-catalog.md and registration-only stub docstrings against drift.

Two independent claims, checked here because both are cases of a
hand-maintained artifact asserting something true about RULE_REGISTRY with
nothing enforcing agreement (#130, #124):

- rule-catalog.md is a hand-written markdown table mirroring every registered
  rule's code and severity. #130 found 11 rows whose severity disagreed with
  the registry, and 4 whose description named an entirely different rule
  (FM005/FM006/SK008/SK009) -- all fixed by hand in the same change that added
  this guard. Only code and severity are checked here: Description and
  Auto-fix are prose, and RuleEntry carries no can_fix field to compare
  against.
  # ponytail: description/auto-fix columns unguarded; add a check when they
  # rot again.
- A registration-only stub (a rule function whose body is ``return []``,
  existing purely so RULE_REGISTRY carries its metadata) names its real
  emitter in its docstring's "Always an empty list." sentence. #124 found
  that check_lk001 is not actually a stub -- it holds the real detection body
  -- so a hand-listed stub set would have been wrong from the start; SK008's
  docstring named a function, `_check_skill_name_and_directory`, that exists
  nowhere in the package (the real emitter is `_check_skill_directory_name`).
  This guard reads RULE_REGISTRY directly rather than hand-listing stub
  codes, so a 10th stub is covered automatically.
"""

from __future__ import annotations

import re
from pathlib import Path

import skilllint.plugin_validator as plugin_validator_module
import skilllint.rules
from skilllint.rule_registry import RULE_REGISTRY

CATALOG_PATH = (
    Path(__file__).parents[3]
    / "plugins"
    / "agentskills-skilllint"
    / "skills"
    / "skilllint"
    / "references"
    / "rule-catalog.md"
)

_ROW_PATTERN = re.compile(r"^\|\s*([A-Z]{2}\d{3})\s*\|\s*([a-z /]+?)\s*\|")
_STUB_MARKER = "Always an empty list."
# `[\w.]*` (not `\w*`) so a dotted attribute path like `FrontmatterValidator.
# _extract_frontmatter` captures whole -- `\w*` alone stops at the first
# `.`, silently truncating the capture to just `FrontmatterValidator` and
# letting the hasattr check below pass on the class existing without ever
# checking the named method exists.
_BACKTICKED_SYMBOL = re.compile(r"`([A-Za-z_][\w.]*)")


def _catalog_rows() -> dict[str, str]:
    """Parse {rule_id: severity_cell} from every table row in rule-catalog.md."""
    rows: dict[str, str] = {}
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        match = _ROW_PATTERN.match(line)
        if match is None:
            continue
        rows[match.group(1)] = match.group(2).strip()
    return rows


def test_rule_catalog_codes_match_registry() -> None:
    """Every rule-catalog.md row must name a code that RULE_REGISTRY has, and vice versa."""
    catalog_codes = set(_catalog_rows())
    registry_codes = set(RULE_REGISTRY)
    missing_from_catalog = registry_codes - catalog_codes
    assert not missing_from_catalog, f"RULE_REGISTRY codes missing from rule-catalog.md: {sorted(missing_from_catalog)}"
    extra_in_catalog = catalog_codes - registry_codes
    assert not extra_in_catalog, f"rule-catalog.md codes not in RULE_REGISTRY: {sorted(extra_in_catalog)}"


def test_rule_catalog_severities_match_registry() -> None:
    """Every rule-catalog.md severity must match RULE_REGISTRY's declared severity.

    RULE_REGISTRY is what `skilllint rules` and `skilllint rule <ID>` print,
    so it is the declared contract; a disagreement means the catalog is wrong.
    A row whose severity cell is not a single value (e.g. PA001's
    "error / warning") is skipped -- RuleEntry.severity is a single Literal,
    so there is nothing to compare a compound cell against.
    """
    for rule_id, catalog_severity in _catalog_rows().items():
        if "/" in catalog_severity:
            continue
        registry_severity = RULE_REGISTRY[rule_id].severity
        assert catalog_severity == registry_severity, (
            f"{rule_id}: rule-catalog.md says severity={catalog_severity!r}, RULE_REGISTRY says {registry_severity!r}"
        )


def _resolves(symbol: str) -> bool:
    """True if *symbol* -- a plain name or a dotted `Class.method` path -- exists.

    `hasattr` alone only resolves a single attribute hop, so a dotted path
    (e.g. ``FrontmatterValidator._extract_frontmatter``) is walked one
    segment at a time.
    """
    for module in (plugin_validator_module, skilllint.rules):
        obj = module
        for part in symbol.split("."):
            if not hasattr(obj, part):
                break
            obj = getattr(obj, part)
        else:
            return True
    return False


def test_stub_docstrings_name_a_resolvable_emitter() -> None:
    """A registration-only stub must name a real emitter symbol in backticks.

    Finds stubs by their docstring's "Always an empty list." sentence rather
    than a hand-maintained code list, so it self-scopes to whatever the
    registry actually contains today.
    """
    for code, entry in RULE_REGISTRY.items():
        marker_index = entry.docstring.find(_STUB_MARKER)
        if marker_index == -1:
            continue
        tail = entry.docstring[marker_index + len(_STUB_MARKER) :]
        match = _BACKTICKED_SYMBOL.search(tail)
        assert match is not None, f"{code}: stub docstring must name its emitter in backticks"

        symbol = match.group(1)
        assert _resolves(symbol), (
            f"{code}: stub docstring names `{symbol}` as its emitter, "
            f"but that symbol does not exist in plugin_validator or skilllint.rules"
        )
