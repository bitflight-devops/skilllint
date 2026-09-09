from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = REPO_ROOT / ".pre-commit-hooks.yaml"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


@pytest.fixture
def staged_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "hook-consumer"
    repository.mkdir()
    for command in (
        ["git", "init"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Hook test"],
    ):
        result = _run(command, repository)
        assert result.returncode == 0, result.stderr

    clean_skill = repository / "skills" / "my-skill" / "SKILL.md"
    clean_skill.parent.mkdir(parents=True)
    clean_skill.write_text(
        (REPO_ROOT / "packages/skilllint/tests/fixtures/claude_code/valid_skill.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    invalid_skill = repository / "skills" / "invalid" / "SKILL.md"
    invalid_skill.parent.mkdir(parents=True)
    invalid_skill.write_text(
        (REPO_ROOT / "packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    excluded_skill = repository / "failing-examples" / "SKILL.md"
    excluded_skill.parent.mkdir()
    excluded_skill.write_text(invalid_skill.read_text(encoding="utf-8"), encoding="utf-8")
    (repository / "LICENSE").write_text("test license\n", encoding="utf-8")
    fixable_skill = repository / "skills" / "fixable" / "SKILL.md"
    fixable_skill.parent.mkdir()
    fixable_skill.write_text(
        "---\n"
        "name: fixable-skill\n"
        "description: Use this skill when testing the published fix hook.\n"
        "tools:\n"
        "  - Read\n"
        "  - Grep\n"
        "---\n\n"
        "# Fixable skill\n",
        encoding="utf-8",
    )
    result = _run(["git", "add", "."], repository)
    assert result.returncode == 0, result.stderr
    return repository


def test_published_manifest_keeps_only_documented_hooks_and_current_reference() -> None:
    hooks = YAML(typ="safe").load(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert [hook["id"] for hook in hooks] == ["skilllint", "skilllint-fix"]
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "rev: v1.19.0" in manifest
    assert "bitflight-devops/skilllint@v1.19.0" in readme


def test_skilllint_hook_runs_matching_files_and_skips_unmatched_paths(staged_repository: Path) -> None:
    clean_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint", "--files", "skills/my-skill/SKILL.md"],
        staged_repository,
    )
    invalid_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint", "--files", "skills/invalid/SKILL.md"],
        staged_repository,
    )
    unmatched_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint", "--files", "LICENSE"], staged_repository
    )
    excluded_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint", "--files", "failing-examples/SKILL.md"],
        staged_repository,
    )

    assert clean_result.returncode == 0, clean_result.stdout + clean_result.stderr
    assert invalid_result.returncode == 1, invalid_result.stdout + invalid_result.stderr
    assert "FM010" in invalid_result.stdout
    assert unmatched_result.returncode == 0, unmatched_result.stdout + unmatched_result.stderr
    assert "Skipped" in unmatched_result.stdout
    assert excluded_result.returncode == 0, excluded_result.stdout + excluded_result.stderr
    assert "Skipped" in excluded_result.stdout


def test_skilllint_fix_hook_edits_once_then_is_idempotent(staged_repository: Path) -> None:
    skill_file = staged_repository / "skills" / "fixable" / "SKILL.md"
    before = skill_file.read_text(encoding="utf-8")
    first_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint-fix", "--files", "skills/fixable/SKILL.md"],
        staged_repository,
    )
    after_first_run = skill_file.read_text(encoding="utf-8")
    second_result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint-fix", "--files", "skills/fixable/SKILL.md"],
        staged_repository,
    )

    assert first_result.returncode == 1, first_result.stdout + first_result.stderr
    assert after_first_run != before
    assert "tools: Read, Grep" in after_first_run
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert skill_file.read_text(encoding="utf-8") == after_first_run


def test_prek_smoke_runs_published_check_hook(staged_repository: Path) -> None:
    result = _run(
        ["uv", "run", "prek", "try-repo", str(REPO_ROOT), "skilllint", "--files", "skills/my-skill/SKILL.md"],
        staged_repository,
    )

    assert result.returncode == 0, result.stdout + result.stderr
