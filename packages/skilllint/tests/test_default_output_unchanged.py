"""Prove that the default output of every ``skilllint`` command is unchanged.

The additive ``--json`` work must not alter a single byte of what the CLI prints
without ``--json``. ``baselines/`` holds the output of the real executable, run as
a subprocess, captured from the commit before that work began: stdout and stderr
captured separately and merged (``2>&1``, as ``action.yml`` does), the exit code,
and any file the command writes. This test replays the same invocations and
requires the same result. It must stay green at every migration step.

The one permitted difference is the ``--json`` option line that each command
gains in its ``--help`` screen. For every case whose output contains a help screen
(``Case.prints_help``) this test accepts exactly that: the new output may differ
from the golden only by one inserted ``--json`` option entry, with nothing removed
or changed (:func:`cli_probe.help_delta`).

Do not regenerate the goldens to make this test pass. See
``capture_baselines.py`` for when re-capture is legitimate and how to run it.
"""

from __future__ import annotations

from itertools import starmap
from typing import TYPE_CHECKING

import pytest
from cli_probe import Golden, describe_difference, help_delta, read_golden
from default_output_cases import BASELINES, CASES, Case, Variant, case_endpoints, golden_path, record_case, variants_for

if TYPE_CHECKING:
    from pathlib import Path

_CASE_VARIANTS = [(case, variant) for case in CASES for variant in variants_for(case)]


def _forgive_json_option_line(expected: Golden, actual: Golden) -> Golden:
    """Return *actual* with each stream that only gained the ``--json`` line set to *expected*.

    A stream that changed in any other way is returned untouched, so the
    comparison that follows reports the real difference.
    """
    forgiven: dict[str, str] = {}
    for name in ("stdout", "stderr", "merged"):
        want, got = getattr(expected, name), getattr(actual, name)
        if want is None or got is None:
            continue
        try:
            help_delta(want, got)
        except ValueError:
            continue
        forgiven[name] = want
    return actual.model_copy(update=forgiven)


@pytest.mark.parametrize(
    ("case", "variant"), _CASE_VARIANTS, ids=[f"{case.id}::{variant.id}" for case, variant in _CASE_VARIANTS]
)
def test_default_output_matches_baseline(case: Case, variant: Variant, tmp_path: Path) -> None:
    """Without ``--json``, stdout, stderr, merged output, exit code and written files match the golden."""
    expected = read_golden(golden_path(case, variant))

    with case_endpoints(case) as endpoints:
        actual = record_case(case, variant, tmp_path, endpoints)

    if case.prints_help:
        actual = _forgive_json_option_line(expected, actual)
    difference = describe_difference(expected, actual)
    assert not difference, f"default output of {case.id} in {variant.id} changed:\n{difference}"


def test_every_golden_belongs_to_a_catalogued_case() -> None:
    """No golden is missing, and none is left over from a removed or renamed case."""
    expected = set(starmap(golden_path, _CASE_VARIANTS))
    on_disk = set(BASELINES.rglob("*.json")) - {BASELINES / "MANIFEST.json"}

    assert on_disk == expected


def test_case_ids_are_unique() -> None:
    """Two cases sharing an id would overwrite each other's goldens."""
    ids = [case.id for case in CASES]

    assert len(ids) == len(set(ids))
