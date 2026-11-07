"""Behavior, isolation, and privacy tests for the paired CLI evaluator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError
from scripts import bench_paired as bench
from scripts.bench_paired_ingest import EnvironmentMetadata, Options, validate_git_config


def metadata(version="1", dependency="1"):
    return EnvironmentMetadata(
        python_version="3.12",
        implementation="CPython",
        platform="Linux",
        machine="x86_64",
        executable="/private/python",
        module_origin="/private/skilllint/__init__.py",
        distributions={"skilllint": [version], "other": [dependency]},
    )


@pytest.fixture
def experiment(tmp_path):
    source = tmp_path / "private-client-corpus"
    source.mkdir()
    (source / "client-secret.txt").write_bytes(b"original sensitive content")
    (source / "internal-link").symlink_to("client-secret.txt")
    git = source / ".git"
    (git / "info").mkdir(parents=True)
    (git / "config").write_bytes(b"[core]\nrepositoryformatversion = 0\n")
    (git / "index").write_bytes(b"synthetic private index")
    (git / "info" / "exclude").write_bytes(b"private-exclude\n")
    return Options(
        baseline_python=tmp_path / "baseline-python",
        candidate_python=tmp_path / "candidate-python",
        corpus=source,
        artifacts=tmp_path / "private-artifacts",
        warmups=1,
        pairs=2,
        timeout=5,
        cli_args=["check", "--fix", "."],
    )


@pytest.fixture
def fake_endpoints(monkeypatch):
    calls = []

    def fake_run(command, *, cwd, env, capture_output, check, timeout):
        assert command[1:4] == ["-I", "-m", "skilllint"]
        assert check is False
        assert capture_output is True
        assert timeout > 0
        assert (cwd / "client-secret.txt").read_bytes() == b"original sensitive content"
        assert (cwd / ".git" / "index").read_bytes() == b"synthetic private index"
        assert not (Path(env["HOME"]) / "previous-run").exists()
        (Path(env["HOME"]) / "previous-run").touch()
        (cwd / "client-secret.txt").write_bytes(b"fixed sensitive content")

        calls.append((command, cwd, env))
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=b"private-client-corpus/client-secret.txt: private finding\n",
            stderr=b"private warning\n",
        )

    monkeypatch.setattr(bench.subprocess, "run", fake_run)
    monkeypatch.setattr(bench, "probe_environment", lambda *args: metadata())
    return calls


def test_pair_order_alternates():
    assert [bench.pair_order(index) for index in range(4)] == [
        ("baseline", "candidate"),
        ("candidate", "baseline"),
        ("baseline", "candidate"),
        ("candidate", "baseline"),
    ]


def test_fix_resets_stable_cwd_git_and_home_and_preserves_original(experiment, fake_endpoints):
    bench.evaluate(experiment)
    calls = fake_endpoints
    assert [Path(call[0][0]).name for call in calls] == [
        "baseline-python",
        "candidate-python",
        "candidate-python",
        "baseline-python",
        "baseline-python",
        "candidate-python",
    ]
    assert len({call[1] for call in calls}) == 1
    assert (experiment.corpus / "client-secret.txt").read_bytes() == b"original sensitive content"
    assert (experiment.corpus / "internal-link").readlink() == Path("client-secret.txt")
    assert (experiment.artifacts.stat().st_mode & 0o777) == 0o700
    report = json.loads((experiment.artifacts / "public.json").read_text())
    assert report["complete"] is True
    assert [sample["phase"] for sample in report["samples"]] == ["warmup"] * 2 + ["measured"] * 4
    assert all(sample["wall_seconds"] >= 0 for sample in report["samples"])
    assert all(sample["child_user_seconds"] >= 0 for sample in report["samples"])
    assert len({sample["tree_digest"] for sample in report["samples"]}) == 1
    before = experiment.artifacts / "warmup-0000-baseline" / "git-before" / ".git"
    after = experiment.artifacts / "warmup-0000-baseline" / "git-after" / ".git"
    assert (before / "index").read_bytes() == (after / "index").read_bytes()
    assert (before / "info" / "exclude").read_bytes() == b"private-exclude\n"


def test_public_export_contains_no_private_text(experiment, fake_endpoints):
    bench.evaluate(experiment)
    public = (experiment.artifacts / "public.json").read_text()
    for secret in (
        "private",
        "client",
        "sensitive",
        "warning",
        "finding",
        str(experiment.corpus),
        "check",
        "--fix",
        "other",
    ):
        assert secret not in public
    raw = experiment.artifacts / "warmup-0000-baseline"
    assert b"private finding" in (raw / "stdout").read_bytes()
    assert b"private warning" in (raw / "stderr").read_bytes()
    private = (experiment.artifacts / "metadata.json").read_text()
    assert str(experiment.corpus) in private
    assert "other" in private
    assert (experiment.artifacts / "digest-key").is_file()


@pytest.mark.parametrize("change", ["stdout", "stderr", "returncode", "file", "symlink", "mode", "new-file"])
def test_mismatch_fails_and_keeps_incomplete_evidence(experiment, fake_endpoints, monkeypatch, change):
    original = bench.run_once

    def changed(*args, **kwargs):
        outcome = original(*args, **kwargs)
        if outcome.sample.endpoint != "candidate":
            return outcome
        corpus = args[2]
        if change == "stdout":
            return bench.Outcome(outcome.sample, b"changed", outcome.stderr)
        if change == "stderr":
            return bench.Outcome(outcome.sample, outcome.stdout, b"changed")
        if change == "returncode":
            return bench.Outcome(replace(outcome.sample, returncode=0), outcome.stdout, outcome.stderr)
        if change == "file":
            (corpus / "client-secret.txt").write_bytes(b"different fix")
        if change == "symlink":
            (corpus / "internal-link").unlink()
            (corpus / "internal-link").symlink_to(".git/config")
        if change == "mode":
            (corpus / "client-secret.txt").chmod(0o700)
        if change == "new-file":
            (corpus / "new-file").touch()
        return outcome

    monkeypatch.setattr(bench, "run_once", changed)
    with pytest.raises(bench.EvaluationError, match="parity failed"):
        bench.evaluate(experiment)
    assert len(fake_endpoints) == 2
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False
    assert (experiment.artifacts / "failure.txt").exists()


def test_joint_output_drift_across_pairs_fails(experiment, fake_endpoints, monkeypatch):
    original = bench.run_once

    def changed(*args, **kwargs):
        outcome = original(*args, **kwargs)
        if outcome.sample.phase == "measured":
            return bench.Outcome(outcome.sample, b"both endpoints now differ from warmup", outcome.stderr)
        return outcome

    monkeypatch.setattr(bench, "run_once", changed)
    with pytest.raises(bench.EvaluationError, match="stdout byte parity"):
        bench.evaluate(experiment)
    assert len(fake_endpoints) == 3


@pytest.mark.parametrize("name", ["config", "index", "info/exclude", "HEAD", "packed-refs", "shallow"])
def test_git_input_changes_fail(experiment, fake_endpoints, monkeypatch, name):
    original = bench.subprocess.run

    def changed(command, **kwargs):
        result = original(command, **kwargs)
        (kwargs["cwd"] / ".git" / name).write_bytes(b"modified")
        return result

    monkeypatch.setattr(bench.subprocess, "run", changed)
    with pytest.raises(bench.EvaluationError, match="parity failed"):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False


def test_source_change_never_exports_success(experiment, fake_endpoints, monkeypatch):
    original = bench.run_once

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        (experiment.corpus / "client-secret.txt").write_bytes(b"concurrent source change")
        return result

    monkeypatch.setattr(bench, "run_once", changed)
    with pytest.raises(bench.EvaluationError, match="file content parity"):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False


def test_dependency_drift_refused_before_cli(experiment, fake_endpoints, monkeypatch):
    def probe(python, *_args):
        return metadata(dependency="2" if python == experiment.candidate_python else "1")

    monkeypatch.setattr(bench, "probe_environment", probe)
    with pytest.raises(bench.EvaluationError, match="distribution names/versions differ"):
        bench.evaluate(experiment)
    assert fake_endpoints == []


def test_skilllint_version_difference_is_allowed():
    bench.check_environments(metadata(version="1"), metadata(version="2"))


@pytest.mark.parametrize("field", ["python_version", "implementation", "platform", "machine"])
def test_python_platform_drift_is_refused(field):
    baseline = metadata()
    candidate = metadata()
    setattr(candidate, field, "different")
    with pytest.raises(bench.EvaluationError, match="Python/platform"):
        bench.check_environments(baseline, candidate)


def test_duplicate_distribution_is_refused():
    candidate = metadata()
    candidate.distributions["other"].append("1")
    with pytest.raises(bench.EvaluationError, match="duplicate"):
        bench.check_environments(metadata(), candidate)


@pytest.mark.parametrize("target", ["../outside", "/absolute", "--config=/absolute", "--config=../outside"])
def test_cli_escape_paths_are_refused(experiment, target):
    with pytest.raises(ValidationError, match="relative paths"):
        Options.model_validate({**experiment.model_dump(), "cli_args": ["check", target]})


@pytest.mark.parametrize("target", ["../outside", "/outside"])
def test_escaping_symlinks_are_refused(experiment, target):
    (experiment.corpus / "escape").symlink_to(target)
    with pytest.raises(bench.EvaluationError, match="symlinks"):
        bench.evaluate(experiment)
    assert not experiment.artifacts.exists()


def test_gitfiles_are_refused(experiment):
    nested = experiment.corpus / "nested"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: /private/original/.git")
    with pytest.raises(bench.EvaluationError, match="Git files"):
        bench.evaluate(experiment)


def test_artifacts_inside_source_are_refused(experiment):
    experiment.artifacts = experiment.corpus / "results"
    with pytest.raises(bench.EvaluationError, match="must not contain"):
        bench.evaluate(experiment)


def test_existing_artifacts_are_not_overwritten(experiment):
    experiment.artifacts.mkdir()
    (experiment.artifacts / "keep").write_text("existing")
    with pytest.raises(FileExistsError):
        bench.evaluate(experiment)
    assert (experiment.artifacts / "keep").read_text() == "existing"


def test_environment_does_not_inherit_user_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/private/original")
    monkeypatch.setenv("PYTHONPATH", "/private/source")
    env = bench.controlled_environment(tmp_path)
    assert "GIT_DIR" not in env
    assert "PYTHONPATH" not in env
    assert env["COLUMNS"] == "80"
    assert env["NO_COLOR"] == "1"
    assert env["LC_ALL"] == "C.UTF-8"
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_OPTIONAL_LOCKS"] == "0"


def test_digest_ignores_git_but_is_keyed(experiment):
    first = bench.tree_digest(experiment.corpus, b"first key")
    (experiment.corpus / ".git" / "index").write_bytes(b"volatile index")
    assert bench.tree_digest(experiment.corpus, b"first key") == first
    assert bench.tree_digest(experiment.corpus, b"second key") != first


@given(st.one_of(st.none(), st.integers(), st.lists(st.text())))
def test_metadata_boundary_rejects_invalid_shape(value):
    with pytest.raises(ValidationError):
        EnvironmentMetadata.model_validate(value)


def test_probe_uses_isolated_endpoint_and_strict_metadata(tmp_path, monkeypatch):
    seen = []

    def probe(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=metadata().model_dump_json().encode())

    monkeypatch.setattr(bench.subprocess, "run", probe)
    result = bench.probe_environment(Path(sys.executable), tmp_path, {}, 5)
    assert result == metadata()
    assert seen[0][0][1:3] == ["-I", "-c"]
    assert seen[0][1]["cwd"] == tmp_path


def test_timeout_keeps_raw_evidence_and_incomplete_export(experiment, fake_endpoints, monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], stderr=b"private partial timeout output")

    monkeypatch.setattr(bench.subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        bench.evaluate(experiment)
    report = json.loads((experiment.artifacts / "public.json").read_text())
    assert report["complete"] is False
    assert (experiment.artifacts / "warmup-0000-baseline" / "stderr").read_bytes() == b"private partial timeout output"


def test_main_reports_private_errors_without_content(monkeypatch, capsys):
    monkeypatch.setattr(
        bench, "parse_options", lambda _argv: (_ for _ in ()).throw(ValueError("private source filename"))
    )
    assert bench.main([]) == 2
    assert "private source filename" not in capsys.readouterr().err


def test_exact_public_allowlist(experiment, fake_endpoints):
    bench.evaluate(experiment)
    report = json.loads((experiment.artifacts / "public.json").read_text())
    assert set(report) == {"schema_version", "complete", "metadata_digest", "samples"}
    for sample in report["samples"]:
        assert set(sample) == {
            "phase",
            "pair",
            "endpoint",
            "started_at",
            "wall_seconds",
            "child_user_seconds",
            "child_system_seconds",
            "returncode",
            "stdout_digest",
            "stderr_digest",
            "tree_digest",
        }


@pytest.mark.parametrize(
    "configuration",
    [
        "[include]\npath = /private/config",
        '[includeIf "gitdir:/private"]\npath = /private/config',
        "[core]\nworktree = /private/original",
        "[core]\nexcludesFile = /private/ignore",
        "[core]\nfsmonitor = /private/command",
        "[core]\nhooksPath = /private/hooks",
    ],
)
def test_external_git_configuration_refused(experiment, configuration):
    (experiment.corpus / ".git" / "config").write_text(configuration)
    with pytest.raises(ValueError, match="unsupported"):
        bench.evaluate(experiment)
    assert not experiment.artifacts.exists()


def test_git_parser_rejects_invalid_syntax():
    with pytest.raises(ValueError, match="syntax"):
        validate_git_config("not a Git config", timeout=5)


def test_changed_endpoint_metadata_never_exports_success(experiment, fake_endpoints, monkeypatch):
    calls = []

    def changed(*args):
        calls.append(args)
        return metadata(dependency="2" if len(calls) > 2 else "1")

    monkeypatch.setattr(bench, "probe_environment", changed)
    with pytest.raises(bench.EvaluationError, match="metadata changed"):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False


def test_source_is_checked_after_execution_failure(experiment, fake_endpoints, monkeypatch):
    def failed(*args, **kwargs):
        (experiment.corpus / "client-secret.txt").write_bytes(b"source was changed")
        raise subprocess.TimeoutExpired("private command", 5)

    monkeypatch.setattr(bench, "run_once", failed)
    with pytest.raises(bench.EvaluationError, match="file content parity"):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False


def test_probe_failure_keeps_incomplete_evidence(experiment, monkeypatch):
    def failed(*args):
        raise subprocess.CalledProcessError(1, "private command")

    monkeypatch.setattr(bench, "probe_environment", failed)
    with pytest.raises(subprocess.CalledProcessError):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False
    assert (experiment.artifacts / "failure.txt").exists()


def test_interpreter_symlink_identity_preserved(tmp_path):
    interpreter = tmp_path / "virtualenv-python"
    interpreter.symlink_to(sys.executable)
    options = bench.parse_options([
        "--baseline-python",
        str(interpreter),
        "--candidate-python",
        str(interpreter),
        "--corpus",
        str(tmp_path / "source"),
        "--artifacts",
        str(tmp_path / "output"),
        "--timeout",
        "5",
        "--",
        "check",
        ".",
    ])
    assert options.baseline_python == interpreter
    assert options.cli_args == ["check", "."]


def test_new_gitfile_cannot_escape_parity(experiment, fake_endpoints, monkeypatch):
    original = bench.subprocess.run

    def changed(command, **kwargs):
        result = original(command, **kwargs)
        nested = kwargs["cwd"] / "nested"
        nested.mkdir()
        (nested / ".git").write_text("gitdir: /outside")
        return result

    monkeypatch.setattr(bench.subprocess, "run", changed)
    with pytest.raises(bench.EvaluationError, match="parity failed"):
        bench.evaluate(experiment)
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False


def test_git_valueless_boolean_is_supported():
    validate_git_config("[core]\nfilemode\n  bare\n", timeout=5)


def test_git_symlink_to_corpus_file_is_refused(experiment):
    exclude = experiment.corpus / ".git" / "info" / "exclude"
    exclude.unlink()
    exclude.symlink_to("../../client-secret.txt")
    with pytest.raises(bench.EvaluationError, match="Git symlinks"):
        bench.evaluate(experiment)


@pytest.mark.slow
def test_real_isolated_subprocess_and_fix_reset(tmp_path):
    import venv

    endpoint = tmp_path / "endpoint"
    venv.EnvBuilder(with_pip=False).create(endpoint)
    python = endpoint / "bin" / "python"
    query = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True,
        text=True,
        check=True,
    )
    site = Path(query.stdout.strip())
    package = site / "skilllint"
    package.mkdir()
    (package / "__init__.py").touch()
    (package / "__main__.py").write_text(
        "import pathlib, sys\n"
        "assert sys.flags.isolated == 1\n"
        "assert sys.argv[1:] == ['check', '--fix', '.']\n"
        "path = pathlib.Path('input.txt')\n"
        "assert path.read_text() == 'original'\n"
        "path.write_text('fixed')\n"
        "print(pathlib.Path.cwd())\n"
    )
    dist = site / "skilllint-0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: skilllint\nVersion: 0\n")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "input.txt").write_text("original")
    options = Options(
        baseline_python=python,
        candidate_python=python,
        corpus=corpus,
        artifacts=tmp_path / "evidence",
        warmups=0,
        pairs=1,
        timeout=5,
        cli_args=["check", "--fix", "."],
    )
    bench.evaluate(options)
    assert (corpus / "input.txt").read_text() == "original"
    report = json.loads((options.artifacts / "public.json").read_text())
    assert report["complete"] is True
    assert len(report["samples"]) == 2


def test_git_indented_override_cannot_bypass_validation():
    with pytest.raises(ValueError, match="unsupported"):
        validate_git_config("[core]\nfilemode = true\n  worktree = /outside\n", timeout=5)


def test_unexpected_exit_code_fails_even_when_outputs_match(experiment, fake_endpoints, monkeypatch):
    original = bench.subprocess.run

    def failed(command, **kwargs):
        result = original(command, **kwargs)
        result.returncode = 2
        return result

    monkeypatch.setattr(bench.subprocess, "run", failed)
    with pytest.raises(bench.EvaluationError, match="Unexpected CLI exit status"):
        bench.evaluate(experiment)
    assert len(fake_endpoints) == 1
    assert json.loads((experiment.artifacts / "public.json").read_text())["complete"] is False
