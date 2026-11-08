from __future__ import annotations

import json
import shlex
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
GUIDE = ROOT / "docs/usage.md"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["uv", "run", "skilllint", *args], cwd=cwd, text=True, capture_output=True, check=False)


def test_documented_cli_routes_execute_against_fixture(tmp_path: Path) -> None:
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: demo-skill\ndescription: Use this skill when validating a demo plugin.\n---\n\n# Demo\n\nBody.\n",
        encoding="utf-8",
    )

    clean = _run("check", "--no-color", str(skill), cwd=tmp_path)
    assert clean.returncode == 0, clean.stdout + clean.stderr

    tokens = _run("check", "--tokens-only", str(skill), cwd=tmp_path)
    assert tokens.returncode == 0, tokens.stdout + tokens.stderr
    assert tokens.stdout.strip().isdigit()

    invalid = _run("check", "--platform", "not-a-platform", str(skill), cwd=tmp_path)
    assert invalid.returncode == 2
    assert "Unknown platform" in invalid.stdout + invalid.stderr


def test_documented_policy_shape_reports_invalid_input(tmp_path: Path) -> None:
    (tmp_path / ".skilllint.json").write_text(
        json.dumps({"thresholds": {"SK006": 0}, "severity": {"SK006": "not-a-severity"}}), encoding="utf-8"
    )
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: demo-skill\ndescription: Use this skill when testing policy diagnostics.\n---\n\nbody\n",
        encoding="utf-8",
    )
    result = _run("check", "--no-color", str(skill), cwd=tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "SK006" in output
    assert "invalid" in output.lower() or "must" in output.lower()


def test_documented_policy_example_uses_supported_overrides(tmp_path: Path) -> None:
    from skilllint.policy import _load_policy

    guide = GUIDE.read_text(encoding="utf-8")
    section = guide.split("## Rules, thresholds, and severity\n", 1)[1].split("\n## ", 1)[0]
    example = section.split("```json\n", 1)[1].split("\n```", 1)[0]
    config = tmp_path / ".skilllint.json"
    config.write_text(example, encoding="utf-8")
    policy, diagnostics = _load_policy(config)

    assert diagnostics == []
    assert policy.thresholds == {"SK006": 4400, "SK007": 8800}
    assert policy.severity == {"SK006": "warning"}
    assert policy.ignore == {"": ["AS008"], "skills/legacy": ["FM007"]}


@pytest.mark.slow
@pytest.mark.parametrize(
    ("heading", "output_format"),
    [
        ("Full human diagnostics", "full"),
        ("Concise", "concise"),
        ("JSON Lines", "json-lines"),
        ("GitHub annotations", "github"),
        ("GitLab Code Quality", "gitlab"),
        ("JUnit-style XML", "junit"),
    ],
)
def test_output_reference_commands_execute(heading: str, output_format: str, tmp_path: Path) -> None:
    text = (ROOT / "docs/output-formats.md").read_text(encoding="utf-8")
    section = text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    command = section.split("```console\n", 1)[1].splitlines()[0]
    args = shlex.split(command)
    assert args[0] == "skilllint"
    assert args[args.index("--output-format") + 1] == output_format
    if ">" in args:
        args = args[: args.index(">")]
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: INVALID_NAME\ndescription: Use this skill when testing report formats.\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    args[args.index("plugins/my-plugin")] = str(skill)

    result = _run(*args[1:], cwd=tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "FM010" in result.stdout
    if output_format == "json-lines":
        assert all(json.loads(line)["schema_version"] == 1 for line in result.stdout.splitlines())
    elif output_format == "gitlab":
        assert isinstance(json.loads(result.stdout), list)
    elif output_format == "junit":
        assert ET.fromstring(result.stdout).tag == "testsuites"
    elif output_format == "github":
        assert "::error " in result.stdout
    elif output_format == "concise":
        assert "error[FM010]" in result.stdout
