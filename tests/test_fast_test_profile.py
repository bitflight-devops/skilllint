from __future__ import annotations

from pathlib import Path

import scripts.run_fast_tests as fast

ROOT = Path(__file__).parents[1]


def test_fast_runner_excludes_slow_tests_and_forwards_scope(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_pytest_main(args: list[str]) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(fast.pytest, "main", fake_pytest_main)

    assert fast.main(["tests/test_fast_test_profile.py", "-q"]) == 0
    assert calls == [["-m", "not slow", "tests/test_fast_test_profile.py", "-q"]]


def test_fast_runner_rejects_marker_overrides(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_pytest_main(args: list[str]) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(fast.pytest, "main", fake_pytest_main)

    for args in (["-m", "slow"], ["--markexpr", "slow"], ["--markexpr=slow"]):
        try:
            fast.main(args)
        except ValueError as exc:
            assert "owns pytest marker selection" in str(exc)
        else:
            raise AssertionError(f"marker override was accepted: {args!r}")

    assert calls == []


def test_agent_contract_distinguishes_fast_loop_from_full_gate() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "uv run python scripts/run_fast_tests.py" in agents
    assert "excludes tests marked `slow`" in agents
    assert "uv run prek run --all-files" in agents
    assert "uv run pytest" in agents


def test_ci_executes_the_fast_profile() -> None:
    workflow = (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")

    assert "name: Fast Tests" in workflow
    assert "uv run --locked python scripts/run_fast_tests.py" in workflow
