from __future__ import annotations

from pathlib import Path

README = Path(__file__).parents[1] / "README.md"
ACTION_USE = "uses: bitflight-devops/skilllint@"


def test_action_examples_pin_package_version_separately_from_action_ref() -> None:
    lines = README.read_text(encoding="utf-8").splitlines()
    action_lines = [index for index, line in enumerate(lines) if ACTION_USE in line]

    assert action_lines
    for index in action_lines:
        with_index = index + 1
        with_indent = len(lines[with_index]) - len(lines[with_index].lstrip())
        assert lines[with_index].strip() == "with:"

        input_lines = []
        for line in lines[with_index + 1 :]:
            if line and len(line) - len(line.lstrip()) <= with_indent:
                break
            input_lines.append(line.strip())

        versions = [
            input_line.removeprefix("version: ").strip('"').split(".")
            for input_line in input_lines
            if input_line.startswith("version: ")
        ]
        assert any(len(version) == 3 and all(part.isdigit() for part in version) for version in versions), lines[index]


def test_action_outputs_table_documents_every_public_output() -> None:
    readme = README.read_text(encoding="utf-8")

    for output in ("result", "exit-code", "inspected-count", "findings", "tool-python", "tool-version"):
        assert f"| `{output}` |" in readme
