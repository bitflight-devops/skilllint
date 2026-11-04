"""Executable full-report contract, color policy and compatibility boundaries."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest
import typer
from default_output_cases import CORE_VARIANTS, Case, workspace
from json_probe_support import CheckResponse, normalise_svg, parse, run_probe
from typer.testing import CliRunner

from skilllint import plugin_validator
from skilllint.models import ValidationIssue, ValidationResult
from skilllint.reporting_full import human_console
from skilllint.scan_runtime import CheckRun


def _repository_workspace(sandbox, endpoints):
    workspace(sandbox, endpoints)
    (sandbox.case / ".git").mkdir()


@pytest.mark.parametrize("color", ["auto", "always", "never"])
@pytest.mark.parametrize("variant", CORE_VARIANTS, ids=lambda variant: variant.id)
def test_terminal_color_policy(tmp_path, color, variant):
    _, run = run_probe(
        tmp_path,
        Case("full", ("check", "invalid-skill/SKILL.md", "--output-format", "full", "--color", color)),
        variant=variant,
    )
    assert run.returncode == 1
    has_ansi = b"\x1b[" in run.stdout
    if color != "auto":
        assert has_ansi == (color == "always")
    elif variant.profile == "no-color" or variant.profile == "dumb":
        assert not has_ansi
    else:
        assert has_ansi == (variant.tty or variant.profile == "force-color")
    assert b"error[FM010]" in run.stdout
    assert b"name: My_Skill!" in run.stdout
    assert b"^^^^" in run.stdout


@pytest.mark.parametrize("output_format", ["json-lines", "concise", "github", "gitlab", "junit"])
def test_machine_formats_ignore_color_policy(tmp_path, output_format):
    outputs = []
    for color in ("auto", "always", "never"):
        _, run = run_probe(
            tmp_path,
            Case(
                "machine",
                ("check", "invalid-skill/SKILL.md", "--output-format", output_format, "--color", color),
                setup=_repository_workspace,
            ),
            root=color,
        )
        assert run.returncode == 1
        assert b"\x1b" not in run.stdout
        outputs.append(run.stdout)
    assert outputs[0] == outputs[1] == outputs[2]


@pytest.mark.parametrize(
    "args", [("valid_skill.md",), ("invalid-skill/SKILL.md",), ("plug",), ("fixme/SKILL.md", "--fix")]
)
def test_full_status_and_findings_match_legacy_json(tmp_path, args):
    _, actual = run_probe(tmp_path, Case("full", ("check", *args, "--output-format", "full", "--color", "never")))
    _, legacy = run_probe(tmp_path, Case("legacy", ("check", *args, "--json", "--show-progress")), root="legacy")
    response = parse(CheckResponse, legacy)
    assert actual.returncode == legacy.returncode
    for file in response.files:
        for validator in file.validators:
            for issue in validator.issues:
                assert issue.code.encode() in actual.stdout
                assert " ".join(issue.message.split()) in " ".join(actual.stdout.decode().split())


@pytest.mark.parametrize("extension", ["svg", "html"])
def test_full_fix_and_record_collect_once(tmp_path, monkeypatch, extension):
    path = tmp_path / "fixme/SKILL.md"
    path.parent.mkdir()
    path.write_text(
        "---\nname: fixme\ndescription: Use when testing full reports.\ntools:\n  - Read\n  - Grep\n---\nBody.\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    recording = tmp_path / f"out.{extension}"
    result = CliRunner().invoke(
        plugin_validator.app,
        ["check", str(path), "--fix", "--output-format", "full", "--color", "never", "--record", str(recording)],
    )
    assert result.exit_code == 0, result.output
    assert collect.call_count == 1
    assert "  - Read" not in path.read_text()
    assert "fixed" in result.stdout
    assert "fixed" in recording.read_text()


def test_no_color_wins_and_preserves_legacy_layout(tmp_path):
    for output_args in ((), ("--output-format", "full")):
        _, plain = run_probe(
            tmp_path,
            Case("plain", ("check", "invalid-skill/SKILL.md", *output_args, "--no-color")),
            root=f"plain{len(output_args)}",
        )
        _, forced = run_probe(
            tmp_path,
            Case("forced", ("check", "invalid-skill/SKILL.md", *output_args, "--no-color", "--color", "always")),
            root=f"forced{len(output_args)}",
        )
        assert plain.stdout == forced.stdout
        assert b"\x1b" not in forced.stdout


def test_explicit_color_does_not_leak_legacy_rich_markup(tmp_path):
    _, run = run_probe(tmp_path, Case("legacy", ("check", "invalid-skill/SKILL.md", "--color", "never")))
    assert run.returncode == 1
    assert b"[bold]" not in run.stdout
    assert b"[red]" not in run.stdout
    assert b"\x1b" not in run.stdout


def test_legacy_json_recording_is_unchanged(tmp_path):
    captures = []
    for color in (None, "never"):
        args = ("--color", color) if color else ()
        sandbox, run = run_probe(
            tmp_path,
            Case("json", ("check", "invalid-skill/SKILL.md", "--json", "--record", "out.svg", *args)),
            root=color or "default",
        )
        response = parse(CheckResponse, run)
        assert response.status == "failed"
        assert b"content_digest" not in run.stdout
        captures.append(normalise_svg((sandbox.case / "out.svg").read_text()))
    assert captures[0] == captures[1]


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("missing.md",),
        ("valid_skill.md", "--json"),
        ("valid_skill.md", "--tokens-only"),
        ("valid_skill.md", "--check", "--fix"),
    ],
)
def test_full_usage_errors(tmp_path, args):
    _, run = run_probe(tmp_path, Case("usage", ("check", *args, "--output-format", "full")))
    assert run.returncode == 2
    assert run.stdout == b""
    assert run.stderr


def test_action_observes_full_output_after_rendering_once(capsys):
    issue = ValidationIssue(field="test", code="FM001", severity="error", message="Unique finding")
    outcome = CheckRun(
        results={Path("demo.md"): [("test", ValidationResult(passed=False, errors=[issue], warnings=[], info=[]))]},
        fixes=[],
    )
    observed = []

    def callback(run):
        observed.append((run, capsys.readouterr().out))

    with pytest.raises(typer.Exit) as exc:
        plugin_validator._finish_check_action_output(
            outcome,
            callback,
            formatted_output=True,
            full_output=True,
            verbose=False,
            no_color=True,
            show_progress=False,
            show_summary=False,
            record_console=human_console(no_color=True),
            record=None,
        )
    assert exc.value.exit_code == 1
    assert len(observed) == 1
    assert observed[0][0] is outcome
    assert observed[0][1].count("Unique finding") == 1
    assert not capsys.readouterr().out


def test_real_unicode_markdown_link_has_source_excerpt(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "demo/SKILL.md"
    path.parent.mkdir()
    path.write_bytes(
        b"---\r\nname: demo\r\ndescription: Use when checking links\r\n---\r\n"
        + "é\t[broken](./missing-界.md)\r\n".encode()
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    result = CliRunner().invoke(
        plugin_validator.app, ["check", str(path), "--output-format", "full", "--color", "never"]
    )
    assert result.exit_code == 1
    assert "error[LK001]" in result.stdout
    assert "demo/SKILL.md:5:12" in result.stdout
    assert "5 | é       [broken](./missing-界.md)" in result.stdout
    assert "^^^^^^^^^^^^^^^" in result.stdout


def test_main_action_full_collects_only_once(tmp_path, monkeypatch, capsys):
    path = tmp_path / "demo/SKILL.md"
    path.parent.mkdir()
    path.write_text("---\nname: Bad_Name\ndescription: Use when checking output.\n---\nBody.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    collect = Mock(wraps=plugin_validator.collect_validation_results)
    monkeypatch.setattr(plugin_validator, "collect_validation_results", collect)
    observed = []

    def callback(run):
        observed.append((run, capsys.readouterr().out))

    with pytest.raises(typer.Exit) as exc:
        plugin_validator.main(
            ctx=Mock(invoked_subcommand=None), paths=[path], output_format="full", color="never", action_report=callback
        )
    assert exc.value.exit_code == 1
    assert collect.call_count == 1
    assert len(observed) == 1
    assert observed[0][1].count("error[FM010]") == 1
    assert not capsys.readouterr().out


def _assert_visible_svg_clip_paths(path: Path) -> None:
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    ids = {element.get("id") for element in root.iter()}
    visible = [
        element for element in root.iter() if element.tag.endswith("}text") and element.text and element.text.strip()
    ]
    assert any("docs:" in (element.text or "") for element in visible)
    for element in visible:
        clip = element.get("clip-path")
        if clip:
            assert clip.removeprefix("url(#").removesuffix(")") in ids


def test_full_svg_recording_preserves_stdout_and_final_diagnostic(tmp_path):
    args = ("check", "invalid-skill/SKILL.md", "--output-format", "full", "--color", "never")
    _, plain = run_probe(tmp_path, Case("plain", args), root="plain")
    sandbox, recorded = run_probe(tmp_path, Case("recorded", (*args, "--record", "out.svg")), root="recorded")
    assert plain.returncode == recorded.returncode == 1
    assert plain.stdout == recorded.stdout
    _assert_visible_svg_clip_paths(sandbox.case / "out.svg")


def test_action_full_svg_recording_preserves_stdout_and_final_diagnostic(tmp_path, monkeypatch, capsys):
    path = tmp_path / "demo/SKILL.md"
    path.parent.mkdir()
    path.write_text("---\nname: Bad_Name\ndescription: Use when checking output.\n---\nBody.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    outputs = []
    for record in (None, tmp_path / "action.svg"):
        callback = Mock()
        with pytest.raises(typer.Exit) as exc:
            plugin_validator.main(
                ctx=Mock(invoked_subcommand=None),
                paths=[path],
                output_format="full",
                color="never",
                record=record,
                action_report=callback,
            )
        assert exc.value.exit_code == 1
        callback.assert_called_once()
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]
    _assert_visible_svg_clip_paths(tmp_path / "action.svg")
