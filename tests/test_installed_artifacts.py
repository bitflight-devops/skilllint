from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
ASSERTION_SCRIPT = REPO_ROOT / "scripts" / "assert_installed_artifact.py"


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
