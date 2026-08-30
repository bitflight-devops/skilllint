"""Parity tests binding rule documentation references to a single source.

Every rule code must resolve to the same documentation reference no matter
which entry point produces it, so that a finding emitted by a rule module and
the same finding emitted by the validator never disagree.
"""

from __future__ import annotations

import pytest

from skilllint.plugin_validator import ErrorCode, generate_docs_url
from skilllint.rule_registry import rule_reference


@pytest.mark.parametrize("code", list(ErrorCode), ids=str)
def test_generate_docs_url_matches_rule_reference_for_every_error_code(code: ErrorCode) -> None:
    """generate_docs_url delegates to rule_reference for every ErrorCode member."""
    assert generate_docs_url(code) == rule_reference(code.value)


def test_generate_docs_url_accepts_bare_code_strings() -> None:
    """Rule modules pass literal codes, so strings must resolve identically to enum members."""
    assert generate_docs_url("FM007") == generate_docs_url(ErrorCode.FM007)


def test_rule_reference_normalises_case() -> None:
    """A lowercase code resolves to the same reference as its canonical uppercase form."""
    assert rule_reference("fm007") == rule_reference("FM007")
