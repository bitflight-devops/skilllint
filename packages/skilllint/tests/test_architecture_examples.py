from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from skilllint.adapters import PlatformAdapter, load_adapters
from skilllint.plugin_validator import app, validate_single_path
from skilllint.rule_registry import get_rule, list_rules

ROOT = Path(__file__).parents[3]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_architecture_names_current_runtime_seams() -> None:
    text = _read("docs/architecture.md")
    for symbol in (
        "plugin_validator.main",
        "_resolve_filter_and_expand_paths",
        "_discover_validatable_paths",
        "_discover_plugin_paths",
        "detect_scan_context",
        "run_validation_loop",
        "validate_single_path",
        "PlatformAdapter",
        "load_adapters",
        "skilllint rules",
        "skilllint rule CODE",
    ):
        assert symbol in text


def test_maintainer_example_is_complete_and_protocol_compatible() -> None:
    text = _read("docs/maintainer-extension-guide.md")
    assert '[project.entry-points."skilllint.adapters"]' in text
    assert all(
        f"def {name}(" in text for name in ("id", "path_patterns", "applicable_rules", "constraint_scopes", "validate")
    )
    sample = re.search(r"```python\n(?P<sample>.*?class ExampleAdapter:.*?)(?:```)", text, re.DOTALL)
    assert sample is not None
    assert all(
        name in sample.group("sample")
        for name in ("id", "path_patterns", "applicable_rules", "constraint_scopes", "validate")
    )
    assert isinstance(load_adapters()[0], PlatformAdapter)
    assert callable(validate_single_path)


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
        "example = 'example_skilllint:ExampleAdapter'\n[build-system]\n"
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
    adapter_cls = next(
        ep
        for distribution in distributions(path=[str(target)])
        for ep in distribution.entry_points
        if ep.group == "skilllint.adapters" and ep.name == "example"
    ).load()
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


def test_design_documents_label_proposed_boundaries() -> None:
    for path in ("docs/design-rule-provenance-registry.md", "docs/design-markdown-link-conventions.md"):
        assert "Status: proposed design" in _read(path)


def test_typing_policy_states_baseline_and_gate_scope() -> None:
    text = _read("docs/TYPING_POLICY.md")
    assert "Python 3.11" in text
    assert "ty check" in text
    assert "packages/" in text
    assert "pytest" in text
