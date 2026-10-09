"""A path a fixer moves must not stay in use under its old name (skilllint#326).

``NameFormatValidator.fix`` renames a skill folder to match the normalised ``name``.
Everything after the fixer ran -- later fixers, revalidation, the results key, the
recorded fixes, the reporters -- used to keep the path it started with, so the run
ended in ``FileNotFoundError``.

The first group runs the real executable (``cli_probe``). The second group covers the
fixer contract in-process: the relocation itself, its failure path, and the other
fixers that mutate paths during a run and must leave them where they were.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from cli_probe import CliRun, Sandbox, run_cli
from default_output_cases import NO_ENDPOINTS, renamed_folder_workspace

from skilllint import fixing
from skilllint.models import AppliedFix, RelocatingFixer, ValidationResult
from skilllint.plugin_validator import validate_single_path
from skilllint.scan_runtime import _folder_move, _follow_moved_folders
from skilllint.validators.frontmatter import NameFormatValidator
from skilllint.validators.hooks import HookValidator
from skilllint.validators.symlinks import SymlinkTargetValidator

RENAMED_SKILL = "violations-1/SKILL.md"
"""Where ``violations--1/SKILL.md`` lives once ``--fix`` normalised the folder name."""


def run_fix(tmp_path: Path, *args: str) -> tuple[Sandbox, CliRun]:
    """Run ``check violations--1/SKILL.md --fix`` plus *args* in a fresh sandbox."""
    sandbox = Sandbox.create(tmp_path)
    renamed_folder_workspace(sandbox, NO_ENDPOINTS)
    return sandbox, run_cli(("check", "violations--1/SKILL.md", "--fix", *args), sandbox)


# --- the real executable -----------------------------------------------------


def test_check_fix_on_renamed_folder_finishes_and_reports_the_new_path(tmp_path: Path) -> None:
    """The run ends like any applied ``--fix`` run: exit 0, no traceback, fixes under the new path."""
    sandbox, run = run_fix(tmp_path, "--no-color")

    assert b"Traceback" not in run.stderr
    assert run.returncode == 0
    assert (sandbox.case / RENAMED_SKILL).is_file()
    assert not (sandbox.case / "violations--1").exists()
    stdout = run.stdout.decode()
    assert "Renamed directory to 'violations-1'" in stdout
    assert RENAMED_SKILL in stdout
    assert "violations--1/SKILL.md" not in stdout


def test_check_fix_json_on_renamed_folder_carries_the_new_path(tmp_path: Path) -> None:
    """Under ``--json`` the fixes list and the file list both name the path as it is on disk afterwards."""
    _, run = run_fix(tmp_path, "--json")

    assert b"Traceback" not in run.stderr
    assert run.returncode == 0
    response = json.loads(run.stdout)
    assert {fix["path"] for fix in response["fixes"]} == {RENAMED_SKILL}
    assert "Renamed directory to 'violations-1'" in {fix["description"] for fix in response["fixes"]}
    assert all(file["path"] == RENAMED_SKILL for file in response["files"])


def test_check_fix_on_a_directory_follows_queued_files_into_the_renamed_folder(tmp_path: Path) -> None:
    """A file queued under the folder before the rename is validated at its new path, not reported missing."""
    sandbox = Sandbox.create(tmp_path)
    write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "skills" / "bad--name" / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")

    run = run_cli(("check", ".", "--fix", "--no-color"), sandbox)

    assert b"does not exist" not in run.stderr
    assert b"Traceback" not in run.stderr
    assert run.returncode != 2
    assert (sandbox.case / "skills" / "bad-name" / "CLAUDE.md").is_file()


def test_queued_paths_follow_a_chain_of_nested_folder_renames(tmp_path: Path) -> None:
    """An outer rename and then an inner rename both apply to a file queued under the inner folder."""
    moved = {
        tmp_path / "outer--bad": tmp_path / "outer-bad",
        tmp_path / "outer-bad" / "inner--bad": tmp_path / "outer-bad" / "inner-bad",
    }

    followed = _follow_moved_folders(tmp_path / "outer--bad" / "inner--bad" / "CLAUDE.md", moved)

    assert followed == tmp_path / "outer-bad" / "inner-bad" / "CLAUDE.md"


@pytest.mark.parametrize(
    ("queued", "result", "was_dir", "expected"),
    [
        pytest.param("s/bad--name", "s/bad-name/SKILL.md", True, ("s/bad--name", "s/bad-name"), id="folder-input"),
        pytest.param(
            "s/bad--name/SKILL.md", "s/bad-name/SKILL.md", False, ("s/bad--name", "s/bad-name"), id="file-input"
        ),
        pytest.param(
            "s/SKILL.md", "s/skill-md/SKILL.md", True, ("s/SKILL.md", "s/skill-md"), id="folder-named-skill-md"
        ),
        pytest.param(
            "s/Test-Skill/SKILL.md", "s/test-skill/SKILL.md", False, ("s/Test-Skill", "s/test-skill"), id="case-only"
        ),
        pytest.param("s/fine", "s/fine/SKILL.md", True, None, id="folder-unchanged"),
        pytest.param("plugin", "plugin", True, None, id="plugin-root-key"),
    ],
)
def test_folder_move_detects_a_rename_from_the_spelled_paths(
    queued: str, result: str, was_dir: bool, expected: tuple[str, str] | None
) -> None:
    """A move is a sibling folder with another spelling; nothing else counts."""
    move = _folder_move(Path(queued), Path(result), was_dir=was_dir)

    assert move == (None if expected is None else (Path(expected[0]), Path(expected[1])))


def test_name_format_fix_keeps_a_folder_an_outer_plugin_json_registers(tmp_path: Path) -> None:
    """An inner plugin.json that does not list the folder must not hide an outer one that does."""
    for root, skills in ((tmp_path, ["./nested/skills/bad--name"]), (tmp_path / "nested", [])):
        (root / ".claude-plugin").mkdir(parents=True)
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "p", "skills": skills}), encoding="utf-8"
        )
    skill = write_skill(tmp_path / "nested" / "skills", "bad--name", "bad--name")

    assert NameFormatValidator().fix(skill) == []
    assert skill.is_file()


def test_check_fix_keeps_skipping_a_gitignored_file_inside_a_renamed_folder(tmp_path: Path) -> None:
    """A queued file git ignores stays skipped after its folder is renamed."""
    sandbox = Sandbox.create(tmp_path)
    subprocess.run(["git", "init", "-q", str(sandbox.case)], check=True)
    (sandbox.case / ".gitignore").write_text("CLAUDE.md\n", encoding="utf-8")
    write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "skills" / "bad--name" / "CLAUDE.md").write_text("# Ignored\n", encoding="utf-8")

    run = run_cli(("check", ".", "--fix", "--json", "--show-progress"), sandbox)

    assert [file["path"] for file in json.loads(run.stdout)["files"]] == ["skills/bad-name/SKILL.md"]
    assert (sandbox.case / "skills" / "bad-name" / "CLAUDE.md").is_file()


def test_check_fix_rebases_results_collected_before_the_folder_moved(tmp_path: Path) -> None:
    """A file listed before its skill keeps no stale old-folder path once the skill renames the folder."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (skill.parent / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")

    run = run_cli(
        ("check", "skills/bad--name/CLAUDE.md", "skills/bad--name/SKILL.md", "--fix", "--json", "--show-progress"),
        sandbox,
    )

    response = json.loads(run.stdout)
    assert sorted(file["path"] for file in response["files"]) == [
        "skills/bad-name/CLAUDE.md",
        "skills/bad-name/SKILL.md",
    ]
    assert all("bad--name" not in fix["path"] for fix in response["fixes"])


# --- the fixer contract ------------------------------------------------------


def write_skill(root: Path, folder: str, name: str) -> Path:
    """Write ``root/folder/SKILL.md`` declaring *name* and return its path."""
    skill = root / folder / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(f"---\nname: {name}\ndescription: Use when testing.\n---\n\n# Body\n", encoding="utf-8")
    return skill


def test_name_format_fix_reports_where_it_moved_the_path(tmp_path: Path) -> None:
    """After a rename the fixer names the file's new location; before any fix it names none."""
    skill = write_skill(tmp_path, "bad--name", "bad--name")
    fixer = NameFormatValidator()
    assert isinstance(fixer, RelocatingFixer)
    assert fixer.relocated_path() is None

    fixer.fix(skill)

    assert fixer.relocated_path() == tmp_path / "bad-name" / "SKILL.md"
    assert (tmp_path / "bad-name" / "SKILL.md").is_file()


def test_name_format_fix_forgets_a_relocation_when_run_again(tmp_path: Path) -> None:
    """A fixer instance reused on another path must not report the previous path's move."""
    fixer = NameFormatValidator()
    fixer.fix(write_skill(tmp_path, "bad--name", "bad--name"))
    untouched = write_skill(tmp_path, "fine", "fine")

    fixer.fix(untouched)

    assert fixer.relocated_path() is None


def test_name_format_fix_leaves_the_folder_in_place_when_the_target_exists(tmp_path: Path) -> None:
    """A blocked rename is rolled back: no ``.fmtemp`` folder is left and no move is reported."""
    skill = write_skill(tmp_path, "bad--name", "bad--name")
    occupied = write_skill(tmp_path, "bad-name", "bad-name")
    fixer = NameFormatValidator()

    descriptions = fixer.fix(skill)

    assert fixer.relocated_path() is None
    assert skill.is_file()
    assert occupied.is_file()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad--name", "bad-name"]
    assert not any("Renamed directory" in d for d in descriptions)


@pytest.mark.parametrize("entry", ["./skills/bad--name", "./skills/bad--name/SKILL.md"], ids=["folder", "skill-md"])
def test_name_format_fix_keeps_a_folder_that_plugin_json_registers(entry: str, tmp_path: Path) -> None:
    """A folder ``plugin.json`` lists is left alone: a rename breaks the manifest (PR002), a name-only fix adds FM010."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "p", "skills": [entry]}), encoding="utf-8"
    )
    skill = write_skill(tmp_path / "skills", "bad--name", "bad--name")
    fixer = NameFormatValidator()

    before = skill.read_text(encoding="utf-8")

    descriptions = fixer.fix(skill)

    assert descriptions == []
    assert fixer.relocated_path() is None
    assert skill.read_text(encoding="utf-8") == before


class MovingFixer:
    """Fixer that moves its file to ``moved/`` and says so."""

    def __init__(self) -> None:
        """Start with no move recorded."""
        self.moved_to: Path | None = None

    def validate(self, path: Path) -> ValidationResult:
        """Pass while *path* exists; the fixer is exercised only through ``fix``."""
        return ValidationResult(passed=path.exists(), errors=[], warnings=[], info=[])

    def can_fix(self) -> bool:
        """Return True."""
        return True

    def fix(self, path: Path) -> list[str]:
        """Move *path* into a sibling ``moved`` folder."""
        target = path.parent / "moved" / path.name
        target.parent.mkdir()
        path.rename(target)
        self.moved_to = target
        return ["moved"]

    def relocated_path(self) -> Path | None:
        """Return where :meth:`fix` moved the file."""
        return self.moved_to


class RecordingFixer:
    """Fixer that records the path it is handed."""

    def __init__(self) -> None:
        """Start with no path seen."""
        self.seen: Path | None = None

    def validate(self, path: Path) -> ValidationResult:
        """Pass while *path* exists; the fixer is exercised only through ``fix``."""
        return ValidationResult(passed=path.exists(), errors=[], warnings=[], info=[])

    def can_fix(self) -> bool:
        """Return True."""
        return True

    def fix(self, path: Path) -> list[str]:
        """Record *path*."""
        self.seen = path
        return ["recorded"]


def test_apply_authorized_fixes_hands_later_fixers_the_moved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fixer that runs after a move gets the file's new path; every recorded fix points at it."""
    monkeypatch.setitem(fixing.FIXER_TRIGGER_CODES, "MovingFixer", frozenset({"X001"}))
    monkeypatch.setitem(fixing.FIXER_TRIGGER_CODES, "RecordingFixer", frozenset({"X001"}))
    original = tmp_path / "a.md"
    original.write_text("x", encoding="utf-8")
    mover, recorder = MovingFixer(), RecordingFixer()
    fixes: list[AppliedFix] = []

    outcome = fixing.apply_authorized_fixes(
        [recorder, mover, RecordingFixer()], original, raw_codes={"X001"}, fixes_out=fixes
    )

    assert outcome.applied
    assert outcome.path == tmp_path / "moved" / "a.md"
    assert recorder.seen == original
    assert {fix.path for fix in fixes} == {outcome.path}
    assert [fix.description for fix in fixes] == ["recorded", "moved", "recorded"]


def test_apply_authorized_fixes_keeps_the_path_when_nothing_moves(tmp_path: Path) -> None:
    """With no fixer applied the outcome is the input path and not applied."""
    original = tmp_path / "a.md"

    outcome = fixing.apply_authorized_fixes([], original, raw_codes=set())

    assert (outcome.applied, outcome.path) == (False, original)


def test_validate_single_path_keys_results_by_the_moved_path(tmp_path: Path) -> None:
    """The in-process entry point returns the path the file has after ``--fix``."""
    skill = write_skill(tmp_path, "bad--name", "bad--name")
    fixes: list[AppliedFix] = []

    results = validate_single_path(skill, check=True, fix=True, verbose=False, fixes_out=fixes)

    moved = tmp_path / "bad-name" / "SKILL.md"
    assert list(results) == [moved]
    assert fixes
    assert {fix.path for fix in fixes} == {moved}


def test_fix_outcome_is_falsy_when_nothing_was_applied(tmp_path: Path) -> None:
    """``apply_authorized_fixes`` used to return a bool; its truthiness still means "a fixer applied"."""
    assert not fixing.FixOutcome(applied=False, path=tmp_path)
    assert fixing.FixOutcome(applied=True, path=tmp_path)


def test_validate_single_path_keeps_a_config_that_moved_with_the_folder(tmp_path: Path) -> None:
    """A ``.skilllint.json`` inside the renamed folder still suppresses its codes after ``--fix``."""
    skill = write_skill(tmp_path, "bad--name", "bad--name")
    (skill.parent / ".skilllint.json").write_text(json.dumps({"ignore": {"": ["SK004"]}}), encoding="utf-8")

    results = validate_single_path(skill, check=True, fix=True, verbose=False)

    moved = results[tmp_path / "bad-name" / "SKILL.md"]
    codes = {issue.code for _, result in moved for issue in (*result.errors, *result.warnings, *result.info)}
    assert "SK004" not in codes


# --- other fixers that mutate paths during a run: they keep the path ---------


def test_symlink_fix_replaces_the_link_at_the_same_path(tmp_path: Path) -> None:
    """The symlink fixer unlinks and recreates the link in place; it never relocates."""
    target = tmp_path / "target.md"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to("target.md ")
    fixer = SymlinkTargetValidator()
    assert not isinstance(fixer, RelocatingFixer)

    fixer.fix(tmp_path)

    assert link.is_symlink()
    assert str(link.readlink()) == "target.md"
    assert link.resolve() == target.resolve()


def test_hook_fix_changes_the_mode_of_the_script_and_keeps_hooks_json_in_place(tmp_path: Path) -> None:
    """The hook fixer chmods the script; the path it was handed stays valid."""
    script = tmp_path / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o644)
    hooks = tmp_path / "hooks.json"
    hooks.write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": str(script)}]}]}}),
        encoding="utf-8",
    )
    fixer = HookValidator()
    assert not isinstance(fixer, RelocatingFixer)

    fixer.fix(hooks)

    assert hooks.is_file()
    assert script.is_file()
