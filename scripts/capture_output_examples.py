"""Capture actual CLI stdout and render deterministic colour SVG previews."""

from __future__ import annotations

import argparse
import io
import os
import re
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

CONCISE_COMMAND = (*COMMAND[:-2], "concise", "--no-color", COMMAND[-1])

# The editable version calculation warns in a shallow checkout. Match that
# warning's source and complete two-line form, not arbitrary stderr warnings.
_SHALLOW_CLONE_WARNING = re.compile(
    rb'^[^\r\n]*vcs_versioning[\\/][^\r\n]*:\d+: UserWarning: "[^\r\n]*"'
    rb" is shallow and may cause errors\r?\n  pre_parse\(wd\)\r?\n",
    re.MULTILINE,
)


def canonical_line_endings(data: bytes) -> bytes:
    """Return comparison/viewer bytes with CRLF normalized, preserving all other data."""
    return data.replace(b"\r\n", b"\n")


def _capture(command: tuple[str, ...]) -> bytes:
    """Run the documented failing fixture and return its unmodified stdout.

    Args:
        command: Documented CLI invocation to capture.

    Returns:
        Raw stdout bytes from the CLI.

    Raises:
        RuntimeError: The fixture did not fail validation or emitted diagnostics.
    """
    # Version discovery can warn before the CLI configures its UTF-8 streams.
    # Pin the child encoding so the targeted stderr filter also works there.
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, check=False)
    diagnostics = _SHALLOW_CLONE_WARNING.sub(b"", result.stderr)
    if result.returncode != 1 or diagnostics:
        raise RuntimeError(f"Example capture failed: exit={result.returncode}, stderr={diagnostics.decode('utf-8')}")
    if not result.stdout:
        raise RuntimeError("Example fixture produced no findings")
    return result.stdout


def capture_jsonl() -> bytes:
    """Return unmodified stdout from the JSON Lines example.

    Returns:
        Raw JSONL stdout bytes from the CLI.
    """
    return _capture(COMMAND)


def capture_concise() -> bytes:
    """Return unmodified stdout from the monochrome concise example.

    Returns:
        Raw concise stdout bytes from the CLI.
    """
    return _capture(CONCISE_COMMAND)


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
    console.print(Syntax(canonical_line_endings(raw).decode("utf-8"), "json", theme="monokai", word_wrap=True))
    svg = console.export_svg(title="skilllint · JSON Lines", unique_id="skilllint-json-lines")
    # Match the repository whitespace hook without changing rendered content.
    return "\n".join(line.rstrip() for line in svg.split("\n")).encode("utf-8")


def render_concise(raw: bytes) -> bytes:
    """Render actual concise output without adding diagnostic colours or markup.

    Args:
        raw: Unmodified UTF-8 concise stdout from the example command.

    Returns:
        Deterministic UTF-8 SVG bytes; wrapping affects only the preview.
    """
    # Match the JSONL preview width for consistent README embedding.
    console = Console(file=io.StringIO(), record=True, width=100, force_terminal=True, color_system="truecolor")
    console.print("Concise actual-output preview", style="bold cyan")
    console.print("Visual wrapping only; raw output has one finding per line.", style="dim")
    console.print()
    # A trailing preview blank line keeps Rich's final line clip off the finding.
    console.print(raw.decode("utf-8"), markup=False, highlight=False, emoji=False)
    svg = console.export_svg(title="skilllint · Concise", unique_id="skilllint-concise")
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
    concise = capture_concise()
    artifacts = {
        "json-lines.jsonl": raw,
        "json-lines.svg": render_jsonl(raw),
        "concise.txt": concise,
        "concise.svg": render_concise(concise),
    }
    stale = []
    for name, content in artifacts.items():
        path = OUTPUT / name
        if args.check:
            if not path.is_file() or canonical_line_endings(path.read_bytes()) != canonical_line_endings(content):
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
