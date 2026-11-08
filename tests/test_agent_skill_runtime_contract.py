from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILL = ROOT / "plugins/agentskills-skilllint/skills/skilllint/SKILL.md"
PLUGIN_README = ROOT / "plugins/agentskills-skilllint/README.md"


def test_plugin_invocation_examples_use_manifest_namespace() -> None:
    manifest = json.loads((PLUGIN_README.parent / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    skill = SKILL.read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)[1]
    name = re.search(r"^name: (.+)$", frontmatter, re.MULTILINE)
    skill_name = name.group(1) if name else SKILL.parent.name
    invocation = f"/{manifest['name']}:{skill_name}"
    examples = [line for line in PLUGIN_README.read_text(encoding="utf-8").splitlines() if line.startswith("/")]

    assert examples
    assert all(example.split()[0] == invocation for example in examples)
