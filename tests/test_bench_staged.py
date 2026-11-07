"""Git semantics and measurement boundaries for the staged workflow evaluator."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from scripts import bench_staged as bench
from scripts.bench_paired import EvaluationError


@pytest.fixture
def options(tmp_path: Path) -> bench.Options:
    """Prepare one staged file without depending on installed hook frameworks."""
    source = tmp_path / "source"
    source.mkdir()
    for args in (["init"], ["config", "user.name", "Test"], ["config", "user.email", "test@example.invalid"]):
        subprocess.run(["git", *args], cwd=source, check=True, capture_output=True)
    (source / "SKILL.md").write_text("staged\n")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    hook = tmp_path / "hook"
    hook.write_text(f"#!{sys.executable}\nimport sys\nprint('same findings')\nsys.exit(1)\n")
    hook.chmod(0o700)
    return bench.Options(Path(sys.executable), Path(sys.executable), hook, source, tmp_path / "evidence", 2, 1, 30)


def test_real_index_detects_staging_changes(options: bench.Options) -> None:
    """Working-tree edits preserve index state, staging those edits changes it."""
    env = bench.controlled_environment(options.source)
    before = bench.index_state(options.source, env, options.timeout)
    (options.source / "SKILL.md").write_text("unstaged\n")
    assert bench.index_state(options.source, env, options.timeout) == before
    subprocess.run(["git", "add", "."], cwd=options.source, check=True)
    assert bench.index_state(options.source, env, options.timeout) != before


def test_alternation_and_allowlisted_export(options: bench.Options) -> None:
    """Real subprocesses alternate and exports contain no private outputs/paths."""
    argv_path = options.source.parent / "argv.json"
    options.prek.write_text(
        f"#!{sys.executable}\nimport sys,json\nfrom pathlib import Path\n"
        f"Path({str(argv_path)!r}).write_text(json.dumps(sys.argv[1:]))\nprint('same findings')\nsys.exit(1)\n"
    )
    bench.evaluate(options)
    assert json.loads(argv_path.read_text()) == ["run", "skilllint", "--stage", "pre-commit", "--color", "never"]
    public = (options.artifacts / "public.json").read_text()
    result = json.loads(public)
    assert result["completed"] is True
    assert [row["endpoint"] for row in result["samples"]] == [
        "baseline",
        "candidate",
        "candidate",
        "baseline",
        "baseline",
        "candidate",
    ]
    assert all(row["returncode"] == 1 for row in result["samples"])
    assert "same findings" not in public
    assert str(options.source) not in public
    assert (options.artifacts / "000-baseline" / "index-before").read_bytes() == (
        options.artifacts / "000-baseline" / "index-after"
    ).read_bytes()


def test_file_mutation_fails_closed(options: bench.Options) -> None:
    """A hook that edits input must not yield a completed check-only experiment."""
    options.prek.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nPath('SKILL.md').write_text('changed')\n")
    with pytest.raises(EvaluationError, match="file content parity"):
        bench.evaluate(options)
    assert not json.loads((options.artifacts / "public.json").read_text())["completed"]
    assert (options.source / "SKILL.md").read_text() == "staged\n"


def test_output_drift_fails_closed(options: bench.Options) -> None:
    """Unstable framework output is rejected, never silently normalized."""
    options.prek.write_text(f"#!{sys.executable}\nimport os\nprint(os.getpid())\n")
    with pytest.raises(EvaluationError, match="output/exit parity"):
        bench.evaluate(options)


def test_rejects_nested_artifacts(options: bench.Options) -> None:
    """Refuse recursive copies before creating anything inside the source."""
    with pytest.raises(EvaluationError, match="must not contain"):
        bench.evaluate(replace(options, artifacts=options.source / "nested"))
    assert not (options.source / "nested").exists()


def test_source_mutation_never_publishes_success(options: bench.Options) -> None:
    """A hook editing the original source leaves the export incomplete."""
    target = str(options.source / "SKILL.md")
    options.prek.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nPath({target!r}).write_text('changed')\n")
    with pytest.raises(EvaluationError, match="file content parity"):
        bench.evaluate(options)
    assert not json.loads((options.artifacts / "public.json").read_text())["completed"]


def test_index_mutation_fails_closed(options: bench.Options) -> None:
    """Index-only mutations are rejected independently of worktree parity."""
    options.prek.write_text(
        f"#!{sys.executable}\nimport subprocess\n"
        "subprocess.run(['git','rm','--cached','SKILL.md'],check=True,capture_output=True)\n"
    )
    with pytest.raises(EvaluationError, match="index semantics changed"):
        bench.evaluate(options)
    assert not json.loads((options.artifacts / "public.json").read_text())["completed"]
