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
import ntpath
import subprocess
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from typing import no_type_check

import pytest
from cli_probe import CliRun, Sandbox, run_cli
from default_output_cases import NO_ENDPOINTS, renamed_folder_workspace

from skilllint import fixing, scan_runtime
from skilllint.models import AppliedFix, RelocatingFixer, ValidationIssue, ValidationResult
from skilllint.plugin_validator import validate_single_path
from skilllint.scan_runtime import _folder_move, _follow_moved_folders
from skilllint.validators.frontmatter import NameFormatValidator
from skilllint.validators.hooks import HookValidator
from skilllint.validators.plugins import PluginRegistrationValidator
from skilllint.validators.symlinks import SymlinkTargetValidator

RENAMED_SKILL = "violations-1/SKILL.md"
"""Where ``violations--1/SKILL.md`` lives once ``--fix`` normalised the folder name."""

PLUGIN_MANIFESTS = (
    ".claude-plugin/plugin.json",
    "plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
)


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


def test_check_fix_follows_a_queued_path_that_spells_the_renamed_folder_differently(tmp_path: Path) -> None:
    """A ``..`` spelling of the renamed folder is followed to the new folder, not reported missing."""
    sandbox = Sandbox.create(tmp_path)
    write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "skills" / "bad--name" / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")

    run = run_cli(
        ("check", "skills/bad--name/SKILL.md", "skills/../skills/bad--name/CLAUDE.md", "--fix", "--no-color"), sandbox
    )

    assert b"does not exist" not in run.stderr
    assert b"Traceback" not in run.stderr
    assert run.returncode != 2
    assert (sandbox.case / "skills" / "bad-name" / "CLAUDE.md").is_file()


def test_check_fix_follows_a_queued_symlink_alias_of_the_renamed_folder(tmp_path: Path) -> None:
    """A queued path through a symlink to the renamed folder is followed, not reported missing."""
    sandbox = Sandbox.create(tmp_path)
    write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "skills" / "bad--name" / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")
    (sandbox.case / "alias").symlink_to(sandbox.case / "skills" / "bad--name", target_is_directory=True)

    run = run_cli(("check", "skills/bad--name/SKILL.md", "alias/CLAUDE.md", "--fix", "--no-color"), sandbox)

    assert b"does not exist" not in run.stderr
    assert b"Traceback" not in run.stderr
    assert run.returncode != 2
    assert (sandbox.case / "skills" / "bad-name" / "CLAUDE.md").is_file()


def test_check_fix_follows_a_queued_file_symlink_into_the_renamed_folder(tmp_path: Path) -> None:
    """A queued file symlink to a skill in the renamed folder is followed, not reported missing."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "alias").mkdir()
    (sandbox.case / "alias" / "SKILL.md").symlink_to(skill)

    run = run_cli(("check", "skills/bad--name/SKILL.md", "alias/SKILL.md", "--fix", "--no-color"), sandbox)

    assert b"does not exist" not in run.stderr
    assert b"Traceback" not in run.stderr
    assert run.returncode != 2
    assert (sandbox.case / "skills" / "bad-name" / "SKILL.md").is_file()


def test_check_fix_keeps_skipping_a_queued_skill_folder_ignored_at_its_old_path(tmp_path: Path) -> None:
    """A queued skill folder git ignores by its old SKILL.md path stays skipped after its parent moves."""
    sandbox = Sandbox.create(tmp_path)
    subprocess.run(["git", "init", "-q", str(sandbox.case)], check=True)
    (sandbox.case / ".gitignore").write_text("outer--bad/inner/SKILL.md\n", encoding="utf-8")
    outer = write_skill(sandbox.case, "outer--bad", "outer--bad")
    write_skill(outer.parent, "inner", "inner")

    run = run_cli(("check", "outer--bad/SKILL.md", "outer--bad/inner", "--fix", "--json"), sandbox)

    assert b"Traceback" not in run.stderr
    assert (sandbox.case / "outer-bad" / "inner" / "SKILL.md").is_file()
    assert [file["path"] for file in json.loads(run.stdout)["files"]] == ["outer-bad/SKILL.md"]


@pytest.mark.parametrize("manifest_path", PLUGIN_MANIFESTS)
def test_check_fix_preserves_registered_skills_without_a_platform_override(tmp_path: Path, manifest_path: str) -> None:
    """Default discovery must not let name repair break another platform's registered skill."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    manifest = sandbox.case / manifest_path
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "p", "skills": ["./skills/bad--name"]}), encoding="utf-8")
    original = skill.read_bytes()

    run = run_cli(("check", ".", "--fix", "--json"), sandbox)

    response = json.loads(run.stdout)
    codes = {
        issue["code"] for file in response["files"] for validator in file["validators"] for issue in validator["issues"]
    }
    assert run.returncode == 1
    assert "FM010" in codes
    assert "PR002" not in codes
    assert skill.read_bytes() == original
    assert not (skill.parent.parent / "bad-name").exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["skills"] == ["./skills/bad--name"]


def test_queued_paths_follow_a_chain_of_nested_folder_renames(tmp_path: Path) -> None:
    """An outer rename and then an inner rename both apply to a file queued under the inner folder."""
    moved = {
        tmp_path / "outer--bad": tmp_path / "outer-bad",
        tmp_path / "outer-bad" / "inner--bad": tmp_path / "outer-bad" / "inner-bad",
    }

    followed = _follow_moved_folders(tmp_path / "outer--bad" / "inner--bad" / "CLAUDE.md", moved)

    assert followed == tmp_path / "outer-bad" / "inner-bad" / "CLAUDE.md"


@pytest.mark.parametrize(
    ("queued", "expected"),
    [
        pytest.param("s/../s/bad--name/CLAUDE.md", "s/bad-name/CLAUDE.md", id="dotdot-alias"),
        pytest.param("./s/bad--name/CLAUDE.md", "s/bad-name/CLAUDE.md", id="dot-alias"),
        pytest.param("./s/other/CLAUDE.md", "./s/other/CLAUDE.md", id="unmoved-keeps-spelling"),
    ],
)
def test_queued_aliases_of_a_renamed_folder_follow_the_rename(queued: str, expected: str) -> None:
    """Lexically different spellings of a renamed folder follow it; unmoved paths keep their spelling."""
    followed = _follow_moved_folders(Path(queued), {Path("s/bad--name"): Path("s/bad-name")})

    assert str(followed) == str(Path(expected))


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


@no_type_check  # PureWindowsPath intentionally models Windows Path keys on every test host.
def test_rebase_collected_preserves_diagnostics_for_a_case_only_windows_rename(monkeypatch: pytest.MonkeyPatch) -> None:
    """Equal Windows keys must retain the existing diagnostics under the renamed spelling."""
    monkeypatch.setattr(scan_runtime, "os", SimpleNamespace(sep="\\", path=ntpath))
    old = PureWindowsPath("skills", "Test-Skill")
    new = PureWindowsPath("skills", "test-skill")
    original = old / "CLAUDE.md"
    moved = new / "CLAUDE.md"
    issue = ValidationIssue(field="name", severity="error", message="Existing diagnostic", code="FM010")
    diagnostic = ValidationResult(passed=False, errors=[issue], warnings=[], info=[])
    results = {original: [("frontmatter", diagnostic)]}
    identities = {original: original}

    scan_runtime._rebase_collected(results, [], identities, old, new, canonical_old=old)

    assert [str(path) for path in results] == [str(moved)]
    assert results[moved] == [("frontmatter", diagnostic)]


@pytest.mark.parametrize(
    ("outer_manifest", "inner_manifest"),
    [
        (".claude-plugin/plugin.json", ".claude-plugin/plugin.json"),
        ("plugin.json", ".claude-plugin/plugin.json"),
        (".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"),
    ],
)
def test_name_format_fix_keeps_a_folder_an_outer_plugin_json_registers(
    tmp_path: Path, outer_manifest: str, inner_manifest: str
) -> None:
    """An inner plugin.json that does not list the folder must not hide an outer one that does."""
    for root, manifest_path, skills in (
        (tmp_path, outer_manifest, ["./nested/skills/bad--name"]),
        (tmp_path / "nested", inner_manifest, []),
    ):
        manifest = root / manifest_path
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"name": "p", "skills": skills}), encoding="utf-8")
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


@pytest.mark.parametrize(
    "paths",
    [
        pytest.param(("skills/bad--name/SKILL.md", "skills/../skills/bad--name/CLAUDE.md"), id="queued-alias"),
        pytest.param(("skills/../skills/bad--name/CLAUDE.md", "skills/bad--name/SKILL.md"), id="collected-alias"),
        pytest.param(
            ("skills/../skills/bad--name/SKILL.md", "skills/bad--name/CLAUDE.md"), id="queued-after-aliased-skill"
        ),
        pytest.param(
            ("skills/bad--name/CLAUDE.md", "skills/../skills/bad--name/SKILL.md"), id="collected-before-aliased-skill"
        ),
        pytest.param(
            ("skills/bad--name/SKILL.md", "alias/../bad--name/CLAUDE.md"), id="queued-through-directory-symlink"
        ),
        pytest.param(("skills/bad--name/SKILL.md", "alias/CLAUDE.md"), id="queued-through-renamed-target"),
        pytest.param(("alias/CLAUDE.md", "skills/bad--name/SKILL.md"), id="collected-through-renamed-target"),
    ],
)
def test_check_fix_rebases_lexically_different_paths_to_the_moved_folder(
    tmp_path: Path, paths: tuple[str, str]
) -> None:
    """Queued and collected aliases keep identifying the moved files once the folder is renamed."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (skill.parent / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")
    (sandbox.case / "alias").symlink_to("skills/bad--name", target_is_directory=True)
    assert {(sandbox.case / path).resolve(strict=True) for path in paths} == {skill, skill.parent / "CLAUDE.md"}

    run = run_cli(("check", *paths, "--fix", "--json", "--show-progress"), sandbox)

    assert run.returncode in {0, 1}
    response = json.loads(run.stdout)
    reported = [sandbox.case / file["path"] for file in response["files"]]
    moved_folder = sandbox.case / "skills" / "bad-name"
    assert all(path.is_file() for path in reported)
    assert {path.resolve() for path in reported} == {moved_folder / "SKILL.md", moved_folder / "CLAUDE.md"}
    assert all((sandbox.case / fix["path"]).is_file() for fix in response["fixes"])
    assert not skill.parent.exists()


@pytest.mark.parametrize(
    ("leaf_name", "alias_first", "use_folder"),
    [
        pytest.param("SKILL.md", False, False, id="queued-skill-file"),
        pytest.param("CLAUDE.md", False, False, id="queued-notes-file"),
        pytest.param("CLAUDE.md", True, False, id="collected-notes-file"),
        pytest.param("SKILL.md", False, True, id="queued-skill-folder"),
    ],
)
def test_check_fix_follows_file_symlinks_when_the_target_folder_moves(
    tmp_path: Path, leaf_name: str, alias_first: bool, use_folder: bool
) -> None:
    """A file alias selected before fixing must still report its original target after a rename."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (skill.parent / "CLAUDE.md").write_text("# Original notes\n", encoding="utf-8")
    alias = sandbox.case / "alias" / leaf_name
    alias.parent.mkdir()
    alias.symlink_to(f"../skills/bad--name/{leaf_name}")
    assert alias.resolve(strict=True) == skill.parent / leaf_name
    selected = "alias" if use_folder else f"alias/{leaf_name}"
    real_skill = "skills/bad--name/SKILL.md"
    paths = (selected, real_skill) if alias_first else (real_skill, selected)

    run = run_cli(("check", *paths, "--fix", "--json", "--show-progress"), sandbox)

    assert run.returncode in {0, 1}
    response = json.loads(run.stdout)
    reported = [sandbox.case / file["path"] for file in response["files"]]
    moved_folder = sandbox.case / "skills" / "bad-name"
    assert all(path.is_file() for path in reported)
    assert {path.resolve(strict=True) for path in reported} == {moved_folder / "SKILL.md", moved_folder / leaf_name}
    assert all((sandbox.case / fix["path"]).is_file() for fix in response["fixes"])
    assert not skill.parent.exists()


@pytest.mark.parametrize("ignore_file", [".gitignore", ".pluginvalidatorignore"])
def test_check_fix_keeps_an_originally_ignored_skill_skipped_after_its_parent_moves(
    tmp_path: Path, ignore_file: str
) -> None:
    """An old-path ignore decision survives an outer rename without exposing a nested skill to fixes."""
    sandbox = Sandbox.create(tmp_path)
    subprocess.run(["git", "init", "-q", str(sandbox.case)], check=True)
    outer = write_skill(sandbox.case, "outer--bad", "outer--bad")
    inner = write_skill(outer.parent, "inner", "Inner")
    original_inner = inner.read_bytes()
    (sandbox.case / ignore_file).write_text("outer--bad/inner/SKILL.md\n", encoding="utf-8")

    run = run_cli(("check", "outer--bad", "outer--bad/inner", "--fix", "--json", "--show-progress"), sandbox)

    assert run.returncode == 0
    response = json.loads(run.stdout)
    moved_inner = sandbox.case / "outer-bad" / "inner" / "SKILL.md"
    assert moved_inner.read_bytes() == original_inner
    assert {file["path"] for file in response["files"]} == {"outer-bad/SKILL.md"}
    assert {fix["path"] for fix in response["fixes"]} == {"outer-bad/SKILL.md"}
    assert not outer.parent.exists()


@pytest.mark.parametrize(
    ("paths", "should_fix"),
    [
        pytest.param(("skills/../skills/bad--name/SKILL.md",), False, id="ignored-alias-only"),
        pytest.param(
            ("skills/../skills/bad--name/SKILL.md", "skills/bad--name/SKILL.md"), True, id="ignored-alias-first"
        ),
        pytest.param(
            ("skills/bad--name/SKILL.md", "skills/../skills/bad--name/SKILL.md"), True, id="ignored-alias-last"
        ),
    ],
)
def test_check_fix_preserves_ignore_decisions_for_each_original_path_spelling(
    tmp_path: Path, paths: tuple[str, ...], should_fix: bool
) -> None:
    """An ignored alias keeps its own decision when another spelling selects the same skill."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    original = skill.read_bytes()
    (sandbox.case / ".pluginvalidatorignore").write_text("skills/../skills/bad--name/SKILL.md\n", encoding="utf-8")

    run = run_cli(("check", *paths, "--fix", "--json", "--show-progress"), sandbox)

    assert run.returncode == 0
    response = json.loads(run.stdout)
    moved = sandbox.case / "skills" / "bad-name" / "SKILL.md"
    if should_fix:
        assert moved.is_file()
        assert moved.read_bytes() != original
        assert not skill.exists()
        assert {file["path"] for file in response["files"]} == {"skills/bad-name/SKILL.md"}
        assert {fix["path"] for fix in response["fixes"]} == {"skills/bad-name/SKILL.md"}
    else:
        assert skill.is_file()
        assert skill.read_bytes() == original
        assert not moved.exists()
        assert response["files"] == []
        assert response["fixes"] == []


def test_check_fix_follows_a_move_recorded_through_a_directory_symlink(tmp_path: Path) -> None:
    """The queued parent traversal and symlink-spelled mover identify the same physical folder."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "actual" / "skills", "bad--name", "bad--name")
    (skill.parent / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")
    (sandbox.case / "link").symlink_to("actual/skills", target_is_directory=True)
    paths = ("link/bad--name/SKILL.md", "link/../skills/bad--name/CLAUDE.md")
    assert {(sandbox.case / path).resolve(strict=True) for path in paths} == {skill, skill.parent / "CLAUDE.md"}

    run = run_cli(("check", *paths, "--fix", "--json", "--show-progress"), sandbox)

    assert run.returncode in {0, 1}
    response = json.loads(run.stdout)
    reported = [sandbox.case / file["path"] for file in response["files"]]
    moved_folder = skill.parent.with_name("bad-name")
    assert all(path.is_file() for path in reported)
    assert {path.resolve() for path in reported} == {moved_folder / "SKILL.md", moved_folder / "CLAUDE.md"}
    assert all((sandbox.case / fix["path"]).is_file() for fix in response["fixes"])
    assert not skill.parent.exists()


def test_check_fix_preserves_a_symlink_skill_directory_after_parent_traversal(tmp_path: Path) -> None:
    """Normalizing the parent traversal must keep the skill link as the directory being renamed."""
    sandbox = Sandbox.create(tmp_path)
    skill = write_skill(sandbox.case / "actual", "bad--name", "bad--name")
    (sandbox.case / "skills").mkdir()
    old_link = sandbox.case / "bad--name"
    old_link.symlink_to("actual/bad--name", target_is_directory=True)
    selected = "skills/../bad--name/SKILL.md"
    assert (sandbox.case / selected).resolve(strict=True) == skill

    run = run_cli(("check", selected, "--fix", "--json"), sandbox)

    assert run.returncode in {0, 1}
    moved_link = sandbox.case / "bad-name"
    assert moved_link.is_symlink()
    assert moved_link.readlink() == Path("actual/bad--name")
    assert not old_link.is_symlink()
    assert not old_link.exists()
    assert skill.parent.is_dir()
    assert skill.is_file()
    assert not skill.parent.with_name("bad-name").exists()
    response = json.loads(run.stdout)
    assert {(sandbox.case / file["path"]).resolve(strict=True) for file in response["files"]} == {skill}
    assert all((sandbox.case / fix["path"]).is_file() for fix in response["fixes"])


def test_check_fix_keeps_the_original_queued_file_when_an_alias_target_is_reused(tmp_path: Path) -> None:
    """A later folder occupying the old alias target must not replace the file selected before fixing."""
    sandbox = Sandbox.create(tmp_path)
    first = write_skill(sandbox.case / "skills", "a-b", "a--c")
    second = write_skill(sandbox.case / "skills", "a--b", "a--b")
    original_notes = "# Original first file\n"
    (first.parent / "CLAUDE.md").write_text(original_notes, encoding="utf-8")
    (second.parent / "CLAUDE.md").write_text("# Original second file\n", encoding="utf-8")
    (sandbox.case / "alias").symlink_to("skills/a-b", target_is_directory=True)
    assert (sandbox.case / "alias" / "CLAUDE.md").resolve(strict=True) == first.parent / "CLAUDE.md"

    run = run_cli(
        (
            "check",
            "skills/a-b/SKILL.md",
            "skills/a--b/SKILL.md",
            "alias/CLAUDE.md",
            "--fix",
            "--json",
            "--show-progress",
        ),
        sandbox,
    )

    assert run.returncode in {0, 1}
    response = json.loads(run.stdout)
    reported = [sandbox.case / file["path"] for file in response["files"]]
    moved_first = sandbox.case / "skills" / "a-c"
    moved_second = sandbox.case / "skills" / "a-b"
    assert {path.resolve(strict=True) for path in reported} == {
        moved_first / "SKILL.md",
        moved_first / "CLAUDE.md",
        moved_second / "SKILL.md",
    }
    assert [path.read_text(encoding="utf-8") for path in reported if path.name == "CLAUDE.md"] == [original_notes]
    assert all((sandbox.case / fix["path"]).is_file() for fix in response["fixes"])


def test_name_format_fix_ignores_a_plugin_json_entry_with_a_nul_byte(tmp_path: Path) -> None:
    """A malformed registration is skipped, as the registration parser skips it, instead of raising."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "p", "skills": ["./skills/x\u0000y"]}), encoding="utf-8"
    )
    skill = write_skill(tmp_path / "skills", "bad--name", "bad--name")

    descriptions = NameFormatValidator().fix(skill)

    assert any("Renamed directory" in d for d in descriptions)


def test_check_fix_skips_a_file_gitignore_matches_only_at_its_new_path(tmp_path: Path) -> None:
    """A file that becomes ignored once its folder is renamed is skipped in the same run."""
    sandbox = Sandbox.create(tmp_path)
    subprocess.run(["git", "init", "-q", str(sandbox.case)], check=True)
    (sandbox.case / ".gitignore").write_text("skills/bad-name/CLAUDE.md\n", encoding="utf-8")
    write_skill(sandbox.case / "skills", "bad--name", "bad--name")
    (sandbox.case / "skills" / "bad--name" / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")

    run = run_cli(("check", ".", "--fix", "--json", "--show-progress"), sandbox)

    assert [file["path"] for file in json.loads(run.stdout)["files"]] == ["skills/bad-name/SKILL.md"]


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


@pytest.mark.parametrize("manifest_path", PLUGIN_MANIFESTS)
@pytest.mark.parametrize(
    ("field", "entry"),
    [
        pytest.param("skills", "./skills/bad--name", id="skills-folder"),
        pytest.param("skills", "./skills/bad--name/SKILL.md", id="skills-skill-md"),
        pytest.param("commands", "./skills/bad--name/SKILL.md", id="commands-skill-md"),
        pytest.param("agents", "./skills/bad--name/helper.md", id="agents-file-inside"),
    ],
)
def test_name_format_fix_keeps_a_folder_that_plugin_json_registers(
    field: str, entry: str, manifest_path: str, tmp_path: Path
) -> None:
    """A folder ``plugin.json`` lists is left alone: a rename breaks the manifest (PR002), a name-only fix adds FM010."""
    manifest = tmp_path / manifest_path
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "p", field: [entry]}), encoding="utf-8")
    skill = write_skill(tmp_path / "skills", "bad--name", "bad--name")
    if field == "agents":
        (skill.parent / "helper.md").write_text("# Helper\n", encoding="utf-8")
    fixer = NameFormatValidator()

    before = skill.read_text(encoding="utf-8")
    assert (tmp_path / entry).exists()

    descriptions = fixer.fix(skill)

    assert descriptions == []
    assert fixer.relocated_path() is None
    assert skill.read_text(encoding="utf-8") == before
    assert (tmp_path / entry).exists()


@pytest.mark.parametrize("manifest_path", PLUGIN_MANIFESTS)
def test_name_format_fix_can_rename_a_skill_when_the_manifest_registers_another_skill(
    tmp_path: Path, manifest_path: str
) -> None:
    """An enclosing manifest only prevents a rename when its own registrations would break."""
    skill = write_skill(tmp_path / "skills", "bad--name", "bad--name")
    other = write_skill(tmp_path / "skills", "kept", "kept")
    manifest = tmp_path / manifest_path
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "p", "skills": ["./skills/kept"]}), encoding="utf-8")
    fixer = NameFormatValidator()

    fixer.fix(skill)

    moved = tmp_path / "skills" / "bad-name" / "SKILL.md"
    assert fixer.relocated_path() == moved
    assert moved.is_file()
    assert not skill.exists()
    assert other.is_file()


@pytest.mark.parametrize(
    ("link_inside_skill", "entry"),
    [
        pytest.param(True, "./skills/bad--name/helper.md", id="link-inside"),
        pytest.param(False, "./helper.md", id="target-inside"),
        pytest.param(True, "./skills/other/../bad--name/helper.md", id="link-inside-parent-segment"),
    ],
)
def test_name_format_fix_preserves_a_registration_through_a_symlink(
    tmp_path: Path, link_inside_skill: bool, entry: str
) -> None:
    """Both a registered link inside the folder and a link targeting it depend on the old name."""
    skill = write_skill(tmp_path / "skills", "bad--name", "bad--name")
    inner = skill.parent / "helper.md"
    outer = tmp_path / "helper.md"
    link, target = (inner, outer) if link_inside_skill else (outer, inner)
    target.write_text("# Helper\n", encoding="utf-8")
    link.symlink_to(target)
    (tmp_path / "skills" / "other").mkdir()
    manifest = tmp_path / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"name": "p", "agents": [entry]}), encoding="utf-8")
    assert PluginRegistrationValidator().validate(tmp_path).errors == []
    before = skill.read_bytes()

    assert NameFormatValidator().fix(skill) == []

    assert skill.read_bytes() == before
    assert link.is_file()
    assert link.resolve() == target
    assert PluginRegistrationValidator().validate(tmp_path).errors == []


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
    mover, recorder, later = MovingFixer(), RecordingFixer(), RecordingFixer()
    fixes: list[AppliedFix] = []

    outcome = fixing.apply_authorized_fixes([recorder, mover, later], original, raw_codes={"X001"}, fixes_out=fixes)

    assert outcome.applied
    assert outcome.path == tmp_path / "moved" / "a.md"
    assert recorder.seen == original
    assert later.seen == outcome.path
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


def test_registration_guard_finds_a_manifest_above_a_relative_skill_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skill path relative to a cwd inside the plugin still reaches the manifest above the cwd."""
    write_skill(tmp_path / "skills", "bad--name", "bad--name")
    manifest = tmp_path / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"name": "p", "skills": ["./skills/bad--name"]}), encoding="utf-8")
    monkeypatch.chdir(tmp_path / "skills")

    assert NameFormatValidator._registered_in_plugin_json(Path("bad--name"))
