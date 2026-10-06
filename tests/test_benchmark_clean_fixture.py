"""Verify the benchmark fixture documented as clean produces no findings.

``AGENTS.md`` documents ``tests/fixtures/benchmark-plugin-1000-skills.zip`` as
"clean, no violations (no-op scan)", and the benchmark workflow times it as the
``scan-clean`` scenario. These tests run the real CLI against the extracted
archive, the same way ``scripts/bench_io.py`` does, and assert that property.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

FIXTURE_ZIP = Path(__file__).parent / "fixtures" / "benchmark-plugin-1000-skills.zip"

# Rule identifiers are printed as ``[FM010]``, ``[LK001]`` and similar. The scan
# runs with ``--no-color`` so ANSI sequences do not split the identifier.
RULE_ID_PATTERN = re.compile(r"\[[A-Z]{2,3}\d{3}\]")


@pytest.fixture(scope="module")
def scan_clean_fixture(tmp_path_factory: pytest.TempPathFactory) -> subprocess.CompletedProcess[str]:
    """Extract the clean fixture and scan it once with the real CLI.

    Args:
        tmp_path_factory: pytest factory for module-scoped temporary directories.

    Returns:
        The completed ``skilllint check`` process for the extracted plugin tree.
    """
    plugin_dir = tmp_path_factory.mktemp("bench-clean")
    with zipfile.ZipFile(FIXTURE_ZIP) as archive:
        archive.extractall(plugin_dir)
    return subprocess.run(
        [sys.executable, "-m", "skilllint.plugin_validator", "check", "--no-color", str(plugin_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.slow
def test_clean_fixture_scan_exits_zero(scan_clean_fixture: subprocess.CompletedProcess[str]) -> None:
    """The scan of the documented-clean fixture reports success."""
    assert scan_clean_fixture.returncode == 0, scan_clean_fixture.stdout[-2000:] + scan_clean_fixture.stderr[-2000:]


@pytest.mark.slow
def test_clean_fixture_scan_reports_no_rule_findings(scan_clean_fixture: subprocess.CompletedProcess[str]) -> None:
    """The scan of the documented-clean fixture prints no rule identifier."""
    findings = sorted(set(RULE_ID_PATTERN.findall(scan_clean_fixture.stdout + scan_clean_fixture.stderr)))
    assert findings == []
