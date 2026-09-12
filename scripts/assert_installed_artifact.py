#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.13.5"]
# ///
"""Verify the installed wheel or source-distribution CLI contract."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

ALIASES: Final = ("agentlint", "pluginlint", "skillint", "skilllint")
WHEEL_PYTHONS: Final = ("3.11", "3.12", "3.13", "3.14")


class _ArtifactEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    head_sha: str
    requested_python: str
    actual_interpreter: str
    actual_python: str
    installed_version: str
    artifact_type: str
    artifact_name: str
    import_path: str
    alias_exits: dict[str, int]
    quickstart_diagnostic: str
    diagnostic_exit: int
    offline_token_result: bool
    cache_root: str
    job: str
    mode: str


class _ImportObservation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    interpreter: str
    python: str
    path: str
    module_version: str
    distribution_version: str


def _python(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _executable(venv_path: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name


def _environment(cache_directory: Path) -> dict[str, str]:
    return {
        **{
            key: value
            for key, value in os.environ.items()
            if key.upper() not in {"NO_PROXY", "PYTHONPATH", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}
        },
        "ALL_PROXY": "http://127.0.0.1:1",
        "DATA_GYM_CACHE_DIR": str(cache_directory),
        "HTTP_PROXY": "http://127.0.0.1:1",
        "HTTPS_PROXY": "http://127.0.0.1:1",
        "TIKTOKEN_CACHE_DIR": str(cache_directory),
    }


def _expected_version(artifact: Path) -> str:
    name = artifact.name.removeprefix("skilllint-")
    if artifact.suffix == ".whl":
        return name.split("-", maxsplit=1)[0]
    return name.removesuffix(".tar.gz")


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise RuntimeError(detail)


def _assert_import(
    installed: Path, python: Path, workspace: Path, env: dict[str, str], version: str
) -> tuple[str, str, str, str]:
    imported = _run(
        [
            str(python),
            "-c",
            (
                "import json, sys, skilllint; from importlib.metadata import version; "
                "print(json.dumps({'interpreter': sys.executable, 'python': sys.version.split()[0], "
                "'path': skilllint.__file__, 'module_version': skilllint.__version__, "
                "'distribution_version': version('skilllint')}))"
            ),
        ],
        workspace,
        env,
    )
    _require(imported.returncode == 0, imported.stderr)
    data = _ImportObservation.model_validate_json(imported.stdout)
    _require(Path(data.path).is_relative_to(installed), data.path)
    _require(data.module_version == version, str(data))
    _require(data.distribution_version == version, str(data))
    return data.interpreter, data.python, data.path, data.distribution_version


def _assert_aliases(installed: Path, workspace: Path, env: dict[str, str]) -> dict[str, int]:
    exits: dict[str, int] = {}
    for alias in ALIASES:
        executable = _executable(installed, alias)
        _require(executable.is_file(), str(executable))
        result = _run([str(executable), "--help"], workspace, env)
        _require(result.returncode == 0, result.stderr)
        exits[alias] = result.returncode
    return exits


def _assert_offline_tokens(installed: Path, workspace: Path, env: dict[str, str]) -> bool:
    skill = workspace / "my-skill" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(
        "---\nname: my-skill\ndescription: Validates Claude Code plugin files for schema correctness and required fields.\n"
        "license: MIT\n---\n\n# my-skill\n\nUse this skill when you need to validate Claude Code plugin files.\n",
        encoding="utf-8",
    )
    result = _run(
        [str(_executable(installed, "skilllint")), "check", "--platform", "claude-code", str(skill)], workspace, env
    )
    _require(result.returncode == 0, result.stdout + result.stderr)
    _require("ProxyError" not in result.stderr, result.stderr)
    return True


def _assert_diagnostic(installed: Path, workspace: Path, env: dict[str, str]) -> tuple[str, int]:
    skill = workspace / "invalid" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text(
        "---\nname: My_Skill!\ndescription: This skill has an invalid name that fails AS001.\n---\n\n# My_Skill\n",
        encoding="utf-8",
    )
    result = _run(
        [str(_executable(installed, "skilllint")), "check", "--platform", "claude-code", str(skill)], workspace, env
    )
    _require(result.returncode == 1, result.stderr)
    match = re.search(r"\b(FM\d{3})\b", result.stdout + result.stderr)
    if match is None:
        raise RuntimeError(result.stdout + result.stderr)
    return match.group(1), result.returncode


def _assert_cache_root(installed: Path, workspace: Path, env: dict[str, str]) -> str:
    cache_file = workspace / ".claude" / "vendor" / "sources" / "page-2026.md"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("cached\n", encoding="utf-8")
    result = _run([str(_executable(installed, "skilllint")), "docs", "latest", "page"], workspace, env)
    _require(result.returncode == 0, result.stderr)
    _require(result.stdout.strip().replace("\n", "") == str(cache_file.resolve()), repr(result.stdout))
    return str(cache_file.parent.resolve())


def _artifact_type(artifact: Path) -> str:
    return "wheel" if artifact.suffix == ".whl" else "sdist"


def _assert_installed_artifact(artifact: Path, *, head_sha: str, requested_python: str, job: str) -> _ArtifactEvidence:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        installed = root / "venv"
        workspace = root / "workspace"
        workspace.mkdir()
        venv.create(installed, with_pip=True)
        python = _python(installed)
        clean_env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        offline_env = _environment(root / "cache")
        install = _run(["uv", "pip", "install", str(artifact), "--python", str(python)], workspace, clean_env)
        _require(install.returncode == 0, install.stderr)
        actual_interpreter, actual_python, import_path, installed_version = _assert_import(
            installed, python, workspace, clean_env, _expected_version(artifact)
        )
        alias_exits = _assert_aliases(installed, workspace, clean_env)
        quickstart_diagnostic, diagnostic_exit = _assert_diagnostic(installed, workspace, clean_env)
        return _ArtifactEvidence(
            head_sha=head_sha,
            requested_python=requested_python,
            actual_interpreter=actual_interpreter,
            actual_python=actual_python,
            installed_version=installed_version,
            artifact_type=_artifact_type(artifact),
            artifact_name=artifact.name,
            import_path=import_path,
            alias_exits=alias_exits,
            quickstart_diagnostic=quickstart_diagnostic,
            diagnostic_exit=diagnostic_exit,
            offline_token_result=_assert_offline_tokens(installed, workspace, offline_env),
            cache_root=_assert_cache_root(installed, workspace, clean_env),
            job=job,
            mode="artifact",
        )


def _write_evidence(directory: Path, evidence: _ArtifactEvidence) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{evidence.artifact_type}.json").write_text(evidence.model_dump_json() + "\n", encoding="utf-8")


def _validate_evidence(directory: Path, head_sha: str) -> None:
    records = [
        _ArtifactEvidence.model_validate_json(path.read_text(encoding="utf-8")) for path in directory.rglob("*.json")
    ]
    expected = {("wheel", python) for python in WHEEL_PYTHONS} | {("sdist", "3.11")}
    _require(len(records) == len(expected), f"expected {len(expected)} evidence records, found {len(records)}")
    _require(
        {(record.artifact_type, record.requested_python) for record in records} == expected,
        "unexpected artifact matrix",
    )
    for record in records:
        _require(record.head_sha == head_sha, f"wrong head SHA: {record.head_sha}")
        _require(record.actual_python.startswith(f"{record.requested_python}."), "wrong interpreter")
        _require(record.mode == "artifact", "wrong evidence mode")
        _require(
            record.job == f"installed-artifact ({record.artifact_type}, Python {record.requested_python})", "wrong job"
        )
        _require(set(record.alias_exits) == set(ALIASES), "missing alias result")
        _require(all(exit_code == 0 for exit_code in record.alias_exits.values()), "alias failure")
        _require(record.quickstart_diagnostic == "FM010" and record.diagnostic_exit == 1, "diagnostic mismatch")
        _require(record.offline_token_result, "offline token failure")
        import_path = Path(record.import_path)
        _require("site-packages" in import_path.parts, f"not an installed import: {import_path}")
        _require(
            import_path.is_relative_to(Path(record.actual_interpreter).parent.parent),
            "import belongs to another interpreter",
        )
        site_packages = next(parent for parent in (import_path, *import_path.parents) if parent.name == "site-packages")
        _require(not Path(record.cache_root).is_relative_to(site_packages), "cache root under site-packages")


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", nargs="?", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--head-sha", default="local")
    parser.add_argument("--requested-python", default=f"{sys.version_info.major}.{sys.version_info.minor}")
    parser.add_argument("--job", default="local")
    arguments = parser.parse_args()
    if arguments.evidence_dir is not None:
        _validate_evidence(arguments.evidence_dir, arguments.head_sha)
        return 0
    artifacts = [
        artifact for artifact in (arguments.artifact, arguments.wheel, arguments.sdist) if artifact is not None
    ]
    _require(bool(artifacts), "provide an artifact, --wheel/--sdist, or --evidence-dir")
    _require(
        arguments.evidence_out is not None or len(artifacts) == 1, "--evidence-out is required for multiple artifacts"
    )
    for artifact in artifacts:
        evidence = _assert_installed_artifact(
            artifact.resolve(),
            head_sha=arguments.head_sha,
            requested_python=arguments.requested_python,
            job=arguments.job,
        )
        if arguments.evidence_out is not None:
            _write_evidence(arguments.evidence_out, evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
