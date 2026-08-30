"""Unit tests for NR-series rule registration metadata (nr_series.py).

Covers the NR002 citation fix: NR002's authority previously cited
``https://agentskills.io/specification.md``, a page that documents nothing
about path traversal, plugin boundaries, escaping, or symlinks (verified via
``grep -ci 'traversal|outside|boundary|escape|symlink'`` returning 0 against
the cached specification). NR002's authority must instead cite
``code.claude.com/docs/en/plugins-reference``, which documents the "Path
traversal limitations" section this rule actually enforces.
"""

from __future__ import annotations

from skilllint.rule_registry import RULE_REGISTRY


class TestNR002Authority:
    """NR002's authority metadata must cite a source that documents the
    plugin path-traversal boundary it enforces."""

    def test_nr002_authority_origin_is_code_claude_com(self) -> None:
        """NR002 authority.origin must be code.claude.com, not agentskills.io."""
        entry = RULE_REGISTRY["NR002"]
        assert entry.authority is not None
        assert entry.authority.origin == "code.claude.com"

    def test_nr002_authority_reference_cites_path_traversal_limitations(self) -> None:
        """NR002 authority.reference must point at the real path-traversal section."""
        entry = RULE_REGISTRY["NR002"]
        assert entry.authority is not None
        assert entry.authority.reference is not None
        assert "plugins-reference" in entry.authority.reference
        assert "path-traversal-limitations" in entry.authority.reference

    def test_nr002_docstring_does_not_cite_agentskills_specification(self) -> None:
        """The fabricated agentskills.io/specification.md citation must be gone."""
        entry = RULE_REGISTRY["NR002"]
        assert "agentskills.io/specification" not in entry.docstring
