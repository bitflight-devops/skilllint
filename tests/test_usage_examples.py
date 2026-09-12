from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDE = ROOT / "docs/usage.md"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["uv", "run", "skilllint", *args], cwd=cwd, text=True, capture_output=True, check=False)


def test_usage_guide_keeps_source_blocks_and_contracts() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    required = {
        "Install": ["python -m pip install skilllint", "uv tool install skilllint"],
        "Check, fix, and tokens": [
            "check --platform claude-code",
            "check --platform cursor",
            "check --platform codex",
            "rules --platform agentskills",
            "check --fix",
            "check --tokens-only",
        ],
        "Output and selection": ["--include-gitignore", "--filter-type"],
        "Rules, thresholds, and severity": ['"thresholds"', '"severity"', '"ignore"', "do not merge"],
        "GitHub Action": [
            "bitflight-devops/skilllint@v1.7.0",
            "steps.lint.outputs.result",
            'version: "1.7.0"',
            "exit-code",
        ],
        "Pre-commit": ["id: skilllint", "id: skilllint-fix", "by-file-type"],
    }
    for heading, snippets in required.items():
        start = text.index(f"## {heading}")
        end = text.find("\n## ", start + 1)
        section = text[start:] if end == -1 else text[start:end]
        assert all(snippet in section for snippet in snippets), heading

    assert "check --platform agentskills" not in text
    assert "--fix --platform" not in text


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
