from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from skilllint.plugin_validator import app
from skilllint.rule_registry import get_rule, list_rules

ROOT = Path(__file__).parents[3]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.slow
def test_retained_adapter_sample_installs_loads_and_emits(monkeypatch, cli_runner, tmp_path: Path) -> None:
    package = tmp_path / "example_skilllint"
    package.mkdir()
    (package / "__init__.py").write_text("from .adapter import ExampleAdapter\n", encoding="utf-8")
    sample = re.search(
        r"```python\n(?P<sample>.*?class ExampleAdapter:.*?)(?:```)",
        _read("docs/maintainer-extension-guide.md"),
        re.DOTALL,
    )
    assert sample is not None
    (package / "adapter.py").write_text(sample.group("sample"), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example-skilllint-adapter'\nversion = '0.0.1'\n"
        "requires-python = '>=3.11'\n[project.entry-points.'skilllint.adapters']\n"
        "example = 'example_skilllint.adapter:ExampleAdapter'\n[build-system]\n"
        "requires = ['hatchling']\nbuild-backend = 'hatchling.build'\n"
        "[tool.hatch.build.targets.wheel]\npackages = ['example_skilllint']\n",
        encoding="utf-8",
    )
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist)], check=True, capture_output=True, text=True, cwd=tmp_path
    )
    target = tmp_path / "target"
    wheel = next(dist.glob("*.whl"))
    subprocess.run(
        ["uv", "pip", "install", "--target", str(target), str(wheel)], check=True, capture_output=True, text=True
    )
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlib.metadata import distributions; print(next(ep for d in distributions() for ep in d.entry_points if ep.group == 'skilllint.adapters' and ep.name == 'example').load()().id())",
        ],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": ":".join((str(Path(sys.executable).parent), "/usr/bin")), "PYTHONPATH": str(target)},
    )
    assert probe.stdout.strip() == "example"
    from importlib.metadata import distributions

    import skilllint.plugin_validator as validator

    monkeypatch.syspath_prepend(str(target))
    adapter_entry_point = next(
        ep
        for distribution in distributions(path=[str(target)])
        for ep in distribution.entry_points
        if ep.group == "skilllint.adapters" and ep.name == "example"
    )
    assert adapter_entry_point.value == "example_skilllint.adapter:ExampleAdapter"
    adapter_cls = adapter_entry_point.load()
    monkeypatch.setitem(validator.ADAPTERS, "example", adapter_cls())

    passing = tmp_path / "pass.json"
    failing = tmp_path / "fail.json"
    passing.write_text("{}", encoding="utf-8")
    failing.write_text("{}", encoding="utf-8")
    assert cli_runner.invoke(app, ["check", str(passing), "--platform", "example"]).exit_code == 0
    assert cli_runner.invoke(app, ["check", str(failing), "--platform", "example"]).exit_code == 1


def test_active_catalog_keeps_retired_rules_out_and_public_registration_rules_in() -> None:
    active = {entry.id for entry in list_rules()}
    assert {"PR001", "PR002", "PR005"} <= active
    assert not {"PR003", "PR004", "SK009"} & active
    assert get_rule("PR001") is not None
    assert get_rule("PR002") is not None
    assert get_rule("PR005") is not None
