"""Validated inputs for the paired CLI evaluator."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from subprocess import run as run_git

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class Options(BaseModel):
    """Explicit experiment inputs; CLI paths are kept private."""

    model_config = ConfigDict(extra="forbid")

    baseline_python: Path
    candidate_python: Path
    corpus: Path
    artifacts: Path
    warmups: int = Field(ge=0)
    pairs: int = Field(ge=1)
    timeout: float = Field(gt=0, allow_inf_nan=False)
    cli_args: list[str]

    @field_validator("cli_args")
    @classmethod
    def validate_cli_args(cls, value: list[str]) -> list[str]:
        """Require targets relative to the disposable working directory.

        Returns:
            Arguments without argparse's optional separator.
        """
        arguments = value[1:] if value[:1] == ["--"] else value
        if not arguments:
            raise ValueError("Pass skilllint arguments after --, for example: -- check .")
        for argument in arguments:
            # Also check --option=path. The evaluator is not a security sandbox;
            # this guards accidental writes to the supplied original corpus.
            path = Path(argument.split("=", 1)[-1])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("CLI targets must be relative paths within the disposable corpus")
        return arguments


class EnvironmentMetadata(BaseModel):
    """Strict boundary for metadata reported by each isolated interpreter."""

    model_config = ConfigDict(strict=True, extra="forbid")

    python_version: str
    implementation: str
    platform: str
    machine: str
    executable: str
    module_origin: str
    distributions: dict[str, list[str]]


def validate_git_config(text: str, timeout: float) -> None:
    """Use Git's own grammar to reject external configuration and active hooks.

    Includes are not followed. Only key names cross the validated boundary;
    configuration values and parser errors remain private.
    """
    git = shutil.which("git", path=os.defpath)
    if git is None:
        raise ValueError("Git is required to validate a Git corpus")
    result = run_git(
        [git, "config", "--no-includes", "--null", "--name-only", "--list", "--file", "/dev/stdin"],
        input=text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        cwd="/",
        env={"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    )
    if result.returncode:
        raise ValueError("Unsupported Git configuration syntax")
    keys = TypeAdapter(list[str]).validate_python(result.stdout.rstrip("\0").split("\0"), strict=True)
    prohibited = {"core.worktree", "core.hookspath", "core.fsmonitor", "core.excludesfile", "core.attributesfile"}
    if any(key in prohibited or key.startswith(("include.", "includeif.")) for key in keys):
        raise ValueError("Git includes, path overrides, and active command hooks are unsupported")
