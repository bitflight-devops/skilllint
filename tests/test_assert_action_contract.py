from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "assert_action_contract.py"


def test_assert_action_contract_accepts_matching_outcome() -> None:
    environment = os.environ | {
        "CASE": "clean",
        "ACTION_RESULT": "passed",
        "ACTION_EXIT_CODE": "0",
        "ACTION_INSPECTED_COUNT": "1",
        "ACTION_FINDINGS": "",
        "ACTION_TOOL_PYTHON": "Python 3.11.9",
        "ACTION_TOOL_VERSION": "skilllint 1.19.2",
        "EXPECTED_RESULT": "passed",
        "EXPECTED_EXIT_CODE": "0",
        "EXPECTED_INSPECTED_COUNT": "1",
        "EXPECTED_FINDING": "",
        "EXPECTED_PYTHON_VERSION": "3.11",
        "EXPECTED_PACKAGE_VERSION": "1.19.2",
    }

    result = subprocess.run([sys.executable, SCRIPT], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "case=clean result=passed exit-code=0\n"


def test_assert_action_contract_rejects_missing_expected_finding() -> None:
    environment = os.environ | {
        "CASE": "validation-error",
        "ACTION_RESULT": "failed",
        "ACTION_EXIT_CODE": "1",
        "ACTION_INSPECTED_COUNT": "1",
        "ACTION_FINDINGS": "SK005",
        "ACTION_TOOL_PYTHON": "Python 3.11.9",
        "ACTION_TOOL_VERSION": "skilllint 1.19.2",
        "EXPECTED_RESULT": "failed",
        "EXPECTED_EXIT_CODE": "1",
        "EXPECTED_INSPECTED_COUNT": "1",
        "EXPECTED_FINDING": "FM010",
        "EXPECTED_PYTHON_VERSION": "3.11",
        "EXPECTED_PACKAGE_VERSION": "1.19.2",
    }

    result = subprocess.run([sys.executable, SCRIPT], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 1
    assert "FM010" in result.stderr


def test_assert_action_contract_rejects_unexpected_finding() -> None:
    environment = os.environ | {
        "CASE": "validation-error",
        "ACTION_RESULT": "failed",
        "ACTION_EXIT_CODE": "1",
        "ACTION_INSPECTED_COUNT": "1",
        "ACTION_FINDINGS": "FM010 ZZ999",
        "ACTION_TOOL_PYTHON": "Python 3.11.9",
        "ACTION_TOOL_VERSION": "1.19.2",
        "EXPECTED_RESULT": "failed",
        "EXPECTED_EXIT_CODE": "1",
        "EXPECTED_INSPECTED_COUNT": "1",
        "EXPECTED_FINDING": "FM010",
        "EXPECTED_PYTHON_VERSION": "3.11",
        "EXPECTED_PACKAGE_VERSION": "1.19.2",
    }

    result = subprocess.run([sys.executable, SCRIPT], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 1
    assert "unexpected" in result.stderr


def test_assert_action_contract_rejects_version_suffix_match() -> None:
    environment = os.environ | {
        "CASE": "clean",
        "ACTION_RESULT": "passed",
        "ACTION_EXIT_CODE": "0",
        "ACTION_INSPECTED_COUNT": "1",
        "ACTION_FINDINGS": "",
        "ACTION_TOOL_PYTHON": "Python 3.11.9",
        "ACTION_TOOL_VERSION": "skilllint 11.19.2",
        "EXPECTED_RESULT": "passed",
        "EXPECTED_EXIT_CODE": "0",
        "EXPECTED_INSPECTED_COUNT": "1",
        "EXPECTED_FINDING": "",
        "EXPECTED_PYTHON_VERSION": "3.11",
        "EXPECTED_PACKAGE_VERSION": "1.19.2",
    }

    result = subprocess.run([sys.executable, SCRIPT], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 1
    assert "tool version" in result.stderr


def test_assert_action_contract_accepts_all_expected_grouped_fix_codes() -> None:
    environment = os.environ | {
        "CASE": "warning",
        "ACTION_RESULT": "passed",
        "ACTION_EXIT_CODE": "0",
        "ACTION_INSPECTED_COUNT": "1",
        "ACTION_FINDINGS": "FM004 FM007",
        "ACTION_TOOL_PYTHON": "Python 3.11.9",
        "ACTION_TOOL_VERSION": "skilllint 1.19.2",
        "EXPECTED_RESULT": "passed",
        "EXPECTED_EXIT_CODE": "0",
        "EXPECTED_INSPECTED_COUNT": "1",
        "EXPECTED_FINDING": "FM004 FM007",
        "EXPECTED_PYTHON_VERSION": "3.11",
        "EXPECTED_PACKAGE_VERSION": "1.19.2",
    }

    result = subprocess.run([sys.executable, SCRIPT], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
