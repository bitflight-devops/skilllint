#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# ///
"""Verify the installed wheel or source-distribution CLI contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ALIASES = ("agentlint", "pluginlint", "skillint", "skilllint")


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
        **{key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
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


def _assert_import(installed: Path, python: Path, workspace: Path, env: dict[str, str], version: str) -> None:
    imported = _run(
        [
            str(python),
            "-c",
            (
                "import json, skilllint; from importlib.metadata import version; "
                "print(json.dumps({'path': skilllint.__file__, 'module_version': skilllint.__version__, "
                "'distribution_version': version('skilllint')}))"
            ),
        ],
        workspace,
        env,
    )
    _require(imported.returncode == 0, imported.stderr)
    data = json.loads(imported.stdout)
    _require(Path(data["path"]).is_relative_to(installed), data["path"])
    _require(data["module_version"] == version, str(data))
    _require(data["distribution_version"] == version, str(data))


def _assert_aliases(installed: Path, workspace: Path, env: dict[str, str]) -> None:
    for alias in ALIASES:
        executable = _executable(installed, alias)
        _require(executable.is_file(), str(executable))
        result = _run([str(executable), "--help"], workspace, env)
        _require(result.returncode == 0, result.stderr)


def _assert_offline_tokens(installed: Path, workspace: Path, env: dict[str, str]) -> None:
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


def _assert_diagnostic(installed: Path, workspace: Path, env: dict[str, str]) -> None:
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
    _require("FM010" in result.stdout + result.stderr, result.stdout + result.stderr)


def _assert_cache_root(installed: Path, workspace: Path, env: dict[str, str]) -> None:
    cache_file = workspace / ".claude" / "vendor" / "sources" / "page-2026.md"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("cached\n", encoding="utf-8")
    result = _run([str(_executable(installed, "skilllint")), "docs", "latest", "page"], workspace, env)
    _require(result.returncode == 0, result.stderr)
    _require(result.stdout.strip().replace("\n", "") == str(cache_file.resolve()), repr(result.stdout))


def _assert_installed_artifact(artifact: Path) -> None:
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
        _assert_import(installed, python, workspace, clean_env, _expected_version(artifact))
        _assert_aliases(installed, workspace, clean_env)
        _assert_offline_tokens(installed, workspace, offline_env)
        _assert_diagnostic(installed, workspace, clean_env)
        _assert_cache_root(installed, workspace, clean_env)


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    arguments = parser.parse_args()
    _assert_installed_artifact(arguments.artifact.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
