"""Action environment validation preserves the established input contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from skilllint.boundary.action_inputs_ingest import ActionInputs, parse_action_inputs

BOOLEAN_FIELDS = {
    "CHECK_ONLY": "check_only",
    "FIX": "fix",
    "VERBOSE": "verbose",
    "NO_COLOR": "no_color",
    "TOKENS_ONLY": "tokens_only",
    "SHOW_PROGRESS": "show_progress",
    "SHOW_SUMMARY": "show_summary",
}
OPTIONAL_FIELDS = {"PLATFORM": "platform", "FILTER": "filter_glob", "FILTER_TYPE": "filter_type"}


def test_missing_inputs_preserve_defaults():
    inputs = parse_action_inputs({"UNRELATED": "ignored"})
    assert inputs.paths == [Path()]
    for name in BOOLEAN_FIELDS.values():
        assert getattr(inputs, name) is (name in {"no_color", "show_summary"})
    for name in OPTIONAL_FIELDS.values():
        assert getattr(inputs, name) is None


@pytest.mark.parametrize("value", ["true", "false", "True", "TRUE", "1", "yes", "", " true "])
@given(other=st.text())
def test_booleans_preserve_exact_true_only(value, other):
    for text in (value, other):
        inputs = parse_action_inputs({f"INPUT_{key}": text for key in BOOLEAN_FIELDS})
        for name in BOOLEAN_FIELDS.values():
            assert getattr(inputs, name) is (text == "true")


@given(value=st.text())
def test_paths_preserve_whitespace_splitting(value):
    assert parse_action_inputs({"INPUT_PATHS": value}).paths == [Path(part) for part in value.split()]


@pytest.mark.parametrize("value", ["", " ", "claude-code", "*.md", "unknown"])
@given(other=st.text())
def test_optional_strings_preserve_content(value, other):
    for text in (value, other):
        inputs = parse_action_inputs({f"INPUT_{key}": text for key in OPTIONAL_FIELDS})
        for name in OPTIONAL_FIELDS.values():
            assert getattr(inputs, name) == (text or None)


@pytest.mark.parametrize("key", ["PATHS", *BOOLEAN_FIELDS, *OPTIONAL_FIELDS])
@pytest.mark.parametrize("value", [None, True, 1, [], {}])
def test_non_string_external_values_are_rejected(key, value):
    with pytest.raises(ValidationError):
        ActionInputs.model_validate({f"INPUT_{key}": value})
