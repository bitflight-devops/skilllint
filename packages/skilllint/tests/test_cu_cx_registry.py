"""Registry and adapter-boundary invariants for the CU and CX rule series.

CU (Cursor ``.mdc`` frontmatter) and CX (OpenAI Codex file validation) are
the two rule series where detection was originally owned by a platform
adapter rather than the core validator (see ``rules/cu_series.py`` and
``rules/cx_series.py`` docstrings, "Architectural note — adapter-backed
series"). Per architect spec §8.3, the resolution is: the series module owns
the ``@skilllint_rule`` registration; the adapter imports the module's public
entry point and converts its output to ``list[dict]`` at the adapter
boundary. Before this file, no test exercised that resolution directly for
either series — the only indirect assertion (``test_cursor_mdc_unknown_fields``
in ``test_adapters.py``) contained an ``or c`` tautology that passed for any
non-empty code string.

This module asserts the same invariant set for both series:
    1. CU001/CU002/CX001/CX002 are registered in ``RULE_REGISTRY``.
    2. Their ``platforms`` metadata matches the single owning adapter.
    3. The Cursor adapter's ``validate()`` returns ``list[dict]`` (the
       unchanged external contract).
    4. No raw-dict ``ValidationIssue(...)`` construction remains in
       ``adapters/cursor/adapter.py`` — issues must come from the registered
       rule functions, not be hand-built at the adapter boundary.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

from skilllint.adapters.codex import CodexAdapter
from skilllint.adapters.cursor import CursorAdapter
from skilllint.rule_registry import RULE_REGISTRY

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
CURSOR_FIXTURES = FIXTURES / "cursor"


class TestCuCxRegistration:
    """CU001, CU002, CX001, and CX002 are registered with the correct platform."""

    def test_cu_rules_registered(self) -> None:
        """CU001 and CU002 are present in RULE_REGISTRY."""
        assert {"CU001", "CU002"} <= RULE_REGISTRY.keys()

    def test_cx_rules_registered(self) -> None:
        """CX001 and CX002 are present in RULE_REGISTRY."""
        assert {"CX001", "CX002"} <= RULE_REGISTRY.keys()

    def test_cu_rules_scoped_to_cursor_platform(self) -> None:
        """CU001 and CU002 declare platforms=["cursor"]."""
        assert RULE_REGISTRY["CU001"].platforms == ["cursor"]
        assert RULE_REGISTRY["CU002"].platforms == ["cursor"]

    def test_cx_rules_scoped_to_codex_platform(self) -> None:
        """CX001 and CX002 declare platforms=["codex"]."""
        assert RULE_REGISTRY["CX001"].platforms == ["codex"]
        assert RULE_REGISTRY["CX002"].platforms == ["codex"]


class TestCuCxAdapterOwnership:
    """Only the owning adapter declares CU/CX in its applicable rule prefixes."""

    def test_only_cursor_adapter_owns_cu_series(self) -> None:
        """CU is owned by the Cursor adapter, not Codex."""
        cursor = CursorAdapter()
        codex = CodexAdapter()
        assert "CU" in cursor.applicable_rules()
        assert "CU" not in codex.applicable_rules()

    def test_only_codex_adapter_owns_cx_series(self) -> None:
        """CX is owned by the Codex adapter, not Cursor."""
        cursor = CursorAdapter()
        codex = CodexAdapter()
        assert "CX" in codex.applicable_rules()
        assert "CX" not in cursor.applicable_rules()


class TestCursorAdapterBoundary:
    """The Cursor adapter's external contract and internal construction."""

    def test_validate_returns_list_of_dict(self) -> None:
        """CursorAdapter.validate() returns list[dict], the unchanged external contract."""
        adapter = CursorAdapter()
        violations = adapter.validate(CURSOR_FIXTURES / "invalid_rule.mdc")
        assert isinstance(violations, list)
        assert violations, "expected at least one violation from invalid_rule.mdc"
        assert all(isinstance(v, dict) for v in violations)

    def test_no_raw_validationissue_construction_in_adapter(self) -> None:
        """adapters/cursor/adapter.py never constructs ValidationIssue directly.

        Issues must be produced by the registered CU rule functions
        (via ``validate_mdc_frontmatter``) and only converted to dicts at the
        adapter boundary — not hand-built as raw ``ValidationIssue(...)`` calls.
        """
        import skilllint.adapters.cursor.adapter as cursor_adapter_module

        source = inspect.getsource(cursor_adapter_module)
        tree = ast.parse(source)
        constructor_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "ValidationIssue")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "ValidationIssue")
            )
        ]
        assert constructor_calls == [], (
            f"adapters/cursor/adapter.py must not construct ValidationIssue directly, "
            f"found {len(constructor_calls)} call(s)"
        )
