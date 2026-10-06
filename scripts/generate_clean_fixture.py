"""Generate the clean benchmark fixture zip: skills that produce no lint findings.

Creates ``tests/fixtures/benchmark-plugin-1000-skills.zip`` (or a custom path via
``--output``). ``AGENTS.md`` documents that archive as "clean, no violations
(no-op scan)" and ``.github/workflows/benchmark.yml`` times it as the
``scan-clean`` scenario, so every skill here must pass ``skilllint check``.
``tests/test_benchmark_clean_fixture.py`` runs the real CLI to enforce that.

The sibling ``scripts/generate_violations_fixture.py`` produces the archive that
carries violations on purpose.

Usage::

    uv run python scripts/generate_clean_fixture.py
    uv run python scripts/generate_clean_fixture.py --output path/to/out.zip --count 50
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Final

DEFAULT_OUTPUT: Final[Path] = Path("tests/fixtures/benchmark-plugin-1000-skills.zip")

# The archive name promises 1000 skills.
DEFAULT_COUNT: Final[int] = 1000

# Earliest timestamp the zip format can store; fixed so regenerating the archive
# from unchanged inputs yields identical bytes.
ZIP_EPOCH: Final[tuple[int, int, int, int, int, int]] = (1980, 1, 1, 0, 0, 0)

SKILL_BODY: Final[str] = """\
# {title}

## Overview

This skill exists for benchmark testing and carries no lint findings.
It contains realistic markdown body content so that the linter processes a
representative file size when scanning the plugin.

## Role Identification (Mandatory)

The model must identify its ROLE_TYPE before proceeding with any task.

## When to Use This Skill

Use this skill when you need to:

- Perform the primary task associated with {title}
- Coordinate related sub-tasks across multiple agents
- Validate outputs against acceptance criteria
- Report results in a structured format

## Core Behaviour

1. Receive the task description from the orchestrator.
2. Analyse the inputs and identify required resources.
3. Execute the task using available tools.
4. Return structured results with clear success/failure indicators.

## Output Format

Results are always returned as a structured summary containing:

- Status: success or failure
- Details: human-readable explanation
- Artifacts: any files or data produced

## Notes

- Always verify inputs before processing.
- Prefer idempotent operations where possible.
- Log progress at each major step.
"""


def build_skill_md(n: int) -> str:
    """Assemble a complete, finding-free ``SKILL.md`` for skill number *n*.

    Args:
        n: Skill number (1-based).

    Returns:
        Full file content including YAML frontmatter and markdown body.
    """
    frontmatter = f"""\
name: clean-skill-{n}
description: Benchmark fixture skill number {n}. Use when load testing the skilllint scanner
version: 1.0.0
triggers:
  - when working on clean skill {n}"""
    return f"---\n{frontmatter}\n---\n\n{SKILL_BODY.format(title=f'Clean Skill {n}')}"


def build_plugin_json(count: int) -> str:
    """Build the ``plugin.json`` content for the generated plugin.

    Args:
        count: Total number of skills in the plugin.

    Returns:
        JSON string for the ``plugin.json`` file.
    """
    data = {
        "name": "benchmark-fixture-plugin",
        "version": "1.0.0",
        "description": f"Synthetic plugin with {count} skills for benchmarking skilllint performance",
    }
    return json.dumps(data, indent=2)


def write_entry(archive: zipfile.ZipFile, name: str, content: str) -> None:
    """Write one deflated text entry with the fixed timestamp.

    Args:
        archive: Open zip archive to write to.
        name: Path of the entry inside the archive.
        content: Text content of the entry.
    """
    info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content)


def generate_zip(output: Path, count: int) -> None:
    """Generate the clean benchmark fixture zip file.

    Args:
        output: Destination path for the zip file.
        count: Number of skills to generate.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        write_entry(archive, "plugin.json", build_plugin_json(count))
        for n in range(1, count + 1):
            write_entry(archive, f"skills/clean-skill-{n}/SKILL.md", build_skill_md(n))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate the clean benchmark fixture zip (skills with no lint findings).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Destination path for the generated zip file."
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of skills to generate.")
    return parser.parse_args()


def main() -> None:
    """Entry point: parse arguments, generate the zip, and print a summary."""
    args = parse_args()
    output: Path = args.output
    count: int = args.count

    print(f"Generating {count} skills -> {output}")
    generate_zip(output, count)
    print(f"Done. Wrote {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
