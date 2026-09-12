from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parent.parent
ASSERTION_SCRIPT = REPO_ROOT / "scripts" / "assert_installed_artifact.py"


def _assertion_module() -> ModuleType:
    spec = spec_from_file_location("assert_installed_artifact", ASSERTION_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_proxy_environment_uses_named_endpoint(tmp_path: Path) -> None:
    module = _assertion_module()

    environment = module._environment(tmp_path)

    assert environment["ALL_PROXY"] == module.OFFLINE_PROXY_URL
    assert environment["HTTP_PROXY"] == module.OFFLINE_PROXY_URL
    assert environment["HTTPS_PROXY"] == module.OFFLINE_PROXY_URL


@pytest.fixture(scope="module")
def built_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output_directory = tmp_path_factory.mktemp("artifacts")
    result = subprocess.run(
        ["uv", "build", "--out-dir", str(output_directory)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

    wheel = next(output_directory.glob("*.whl"))
    sdist = next(output_directory.glob("*.tar.gz"))
    return wheel, sdist


@pytest.mark.slow
@pytest.mark.parametrize("artifact_index", [0, 1])
def test_installed_artifact_contract(built_artifacts: tuple[Path, Path], artifact_index: int, tmp_path: Path) -> None:
    artifact = built_artifacts[artifact_index]
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, str(ASSERTION_SCRIPT), str(artifact)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.slow
def test_installed_artifact_writes_observed_evidence(built_artifacts: tuple[Path, Path], tmp_path: Path) -> None:
    wheel, sdist = built_artifacts
    evidence_directory = tmp_path / "evidence"
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}

    result = subprocess.run(
        [
            sys.executable,
            str(ASSERTION_SCRIPT),
            "--wheel",
            str(wheel),
            "--sdist",
            str(sdist),
            "--evidence-out",
            str(evidence_directory),
            "--head-sha",
            "evidence-test-head",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(evidence_directory.glob("*.json"))]
    assert {record["artifact_type"] for record in records} == {"wheel", "sdist"}
    assert all(record["head_sha"] == "evidence-test-head" for record in records)
    assert all("site-packages" in record["import_path"] for record in records)
    assert all(
        record["alias_exits"] == dict.fromkeys(("agentlint", "pluginlint", "skillint", "skilllint"), 0)
        for record in records
    )
    assert all(record["diagnostic_exit"] == 1 for record in records)
    assert all(record["quickstart_diagnostic"] == "FM010" for record in records)
    assert all(record["installed_version"] for record in records)
    assert all(record["offline_token_result"] is True for record in records)
