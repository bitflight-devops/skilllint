"""Capture actual CLI JSONL bytes and render a deterministic colour SVG preview."""

from __future__ import annotations

import argparse
import io
import subprocess
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples/output"
COMMAND = (
    "uv",
    "run",
    "skilllint",
    "check",
    "--platform",
    "claude-code",
    "--output-format",
    "json-lines",
    "examples/output/fixtures/demo-skill/SKILL.md",
)


def capture_jsonl() -> bytes:
    """Run the documented failing fixture and return its unmodified stdout.

    Returns:
        Raw stdout bytes from the CLI.

    Raises:
        RuntimeError: The fixture did not fail validation or emitted diagnostics.
    """
    result = subprocess.run(COMMAND, cwd=ROOT, capture_output=True, check=False)
    if result.returncode != 1 or result.stderr:
        raise RuntimeError(f"Example capture failed: exit={result.returncode}, stderr={result.stderr.decode('utf-8')}")
    if not result.stdout:
        raise RuntimeError("Example fixture produced no findings")
    return result.stdout


def render_jsonl(raw: bytes) -> bytes:
    """Render the exact captured text with syntax colour and visual wrapping.

    Args:
        raw: Unmodified UTF-8 JSONL stdout from the example command.

    Returns:
        Deterministic UTF-8 SVG bytes; wrapping affects only the preview.
    """
    # 100 columns keeps long JSON records readable when embedded in the README.
    console = Console(file=io.StringIO(), record=True, width=100, force_terminal=True, color_system="truecolor")
    console.print("JSONL report preview", style="bold cyan")
    console.print("Visual wrapping only; raw output has one JSON object per line.", style="dim")
    console.print()
    console.print(Syntax(raw.decode("utf-8"), "json", theme="monokai", word_wrap=True))
    svg = console.export_svg(title="skilllint · JSON Lines", unique_id="skilllint-json-lines")
    # Match the repository whitespace hook without changing rendered content.
    return "\n".join(line.rstrip() for line in svg.split("\n")).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    """Regenerate examples, or report drift without modifying committed files.

    Args:
        argv: Optional command-line arguments, defaulting to the process arguments.

    Returns:
        Zero on success, one when checked artifacts are absent or stale.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed examples differ; do not write files.")
    args = parser.parse_args(argv)
    raw = capture_jsonl()
    artifacts = {"json-lines.jsonl": raw, "json-lines.svg": render_jsonl(raw)}
    stale = []
    for name, content in artifacts.items():
        path = OUTPUT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                stale.append(name)
        else:
            path.write_bytes(content)
    if stale:
        print(f"Stale output examples: {', '.join(stale)}")
        print("Regenerate with: uv run python scripts/capture_output_examples.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
