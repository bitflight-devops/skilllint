"""Scan expansion and validation-loop orchestration.

This module provides the runtime seams for:
- Path discovery and expansion
- Validation loop orchestration
- Summary statistics computation

The CLI entrypoint delegates through these functions to keep
plugin_validator.py focused on validation logic rather than
orchestration concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, NoReturn, Protocol

import msgspec.json
import typer

if TYPE_CHECKING:
    from skilllint.plugin_validator import (
        FileResults,
        Reporter,
        ValidationResult,
    )

# Convenience glob patterns for --filter-type option
FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "**/skills/*/SKILL.md",
    "agents": "**/agents/*.md",
    "commands": "**/commands/*.md",
}

# Default patterns for auto-discovering validatable files in bare directories
DEFAULT_SCAN_PATTERNS: tuple[str, ...] = (
    "**/skills/*/SKILL.md",
    "**/agents/*.md",
    "**/commands/*.md",
    "**/.claude-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)


# ============================================================================
# SCAN DISCOVERY MODES (R015, R016, R017)
# ============================================================================


class ScanDiscoveryMode(StrEnum):
    """Discovery mode for scan target selection.

    - MANIFEST: plugin.json explicitly enumerates components (R015)
    - AUTO: plugin.json exists but omits component arrays (R016)
    - STRUCTURE: provider directories without manifest (R017)
    """

    MANIFEST = "manifest"
    AUTO = "auto"
    STRUCTURE = "structure"


@dataclass(frozen=True)
class PluginManifest:
    """Parsed plugin.json with explicit component declarations."""

    path: Path
    name: str | None
    agents: list[str]
    commands: list[str]
    skills: list[str]
    hooks: list[str]

    def has_explicit_components(self) -> bool:
        """Return True if manifest declares explicit components."""
        return bool(self.agents or self.commands or self.skills or self.hooks)


# Provider directory names that indicate structure-based discovery
PROVIDER_DIR_NAMES: frozenset[str] = frozenset({
    ".claude",
    ".agent",
    ".agents", 
    ".gemini",
    ".cursor",
})


def read_plugin_manifest(plugin_dir: Path) -> PluginManifest | None:
    """Read and parse plugin.json from a plugin directory.

    Args:
        plugin_dir: Directory containing .claude-plugin/plugin.json

    Returns:
        PluginManifest if valid plugin.json exists, None otherwise.
    """
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return None

    try:
        data = msgspec.json.decode(plugin_json.read_bytes())
        if not isinstance(data, dict):
            return None
    except (OSError, msgspec.DecodeError):
        return None

    return PluginManifest(
        path=plugin_dir,
        name=data.get("name"),
        agents=data.get("agents", []),
        commands=data.get("commands", []),
        skills=data.get("skills", []),
        hooks=data.get("hooks", []),
    )


def detect_discovery_mode(path: Path) -> ScanDiscoveryMode:
    """Detect the appropriate discovery mode for a scan path.

    Args:
        path: Directory to scan (may contain plugin.json or be a provider dir)

    Returns:
        ScanDiscoveryMode enum value.
    """
    # Check for plugin.json first
    manifest = read_plugin_manifest(path)
    if manifest is not None:
        if manifest.has_explicit_components():
            return ScanDiscoveryMode.MANIFEST
        return ScanDiscoveryMode.AUTO

    # Check if this is a provider directory
    if path.name in PROVIDER_DIR_NAMES:
        return ScanDiscoveryMode.STRUCTURE

    # Check parent for provider directory
    if path.parent.name in PROVIDER_DIR_NAMES:
        return ScanDiscoveryMode.STRUCTURE

    # Default to auto-discovery
    return ScanDiscoveryMode.AUTO


def get_manifest_discovery_paths(manifest: PluginManifest) -> list[Path]:
    """Get scan paths from explicit manifest declarations.

    Args:
        manifest: Parsed plugin manifest with component lists

    Returns:
        List of paths to validate based on manifest declarations.
    """
    paths: list[Path] = []
    root = manifest.path

    for agent in manifest.agents:
        agent_path = root / "agents" / f"{agent}.md"
        if agent_path.exists():
            paths.append(agent_path)

    for command in manifest.commands:
        command_path = root / "commands" / f"{command}.md"
        if command_path.exists():
            paths.append(command_path)

    for skill in manifest.skills:
        skill_path = root / "skills" / skill / "SKILL.md"
        if skill_path.exists():
            paths.append(skill_path)

    for hook in manifest.hooks:
        hook_path = root / "hooks" / f"{hook}.json"
        if hook_path.exists():
            paths.append(hook_path)

    return paths


def get_structure_discovery_paths(path: Path) -> list[Path]:
    """Get scan paths for structure-based discovery.

    Args:
        path: Provider directory path (.claude, .agent, .agents, .gemini, .cursor)

    Returns:
        List of paths to validate based on directory structure.
    """
    patterns: tuple[str, ...]

    if path.name == ".claude" or path.name == ".agent" or path.name == ".agents":
        patterns = (
            "**/*.md",
            "**/hooks.json",
        )
    elif path.name == ".gemini":
        patterns = (
            "**/*.md",
        )
    elif path.name == ".cursor":
        patterns = (
            "**/*.md",
            "**/*.yaml",
            "**/*.yml",
        )
    else:
        # Default for unknown provider directories
        patterns = ("**/*.md",)

    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(path.glob(pattern)))

    return paths


def discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files in a bare directory.

    Globs ``DEFAULT_SCAN_PATTERNS`` against *directory* and returns
    deduplicated, sorted paths.  For any ``.claude-plugin/plugin.json``
    match the **plugin root directory** (grandparent of plugin.json) is
    returned instead of the file itself, because ``detect_file_type``
    recognises directories that contain ``.claude-plugin/plugin.json``.

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    discovered: set[Path] = set()
    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in directory.glob(pattern):
            if match.name == "plugin.json":
                discovered.add(match.parent.parent)
            else:
                discovered.add(match)
    return sorted(discovered)


def resolve_filter_and_expand_paths(
    paths: list[Path],
    filter_glob: str | None,
    filter_type: str | None,
) -> tuple[list[Path], bool]:
    """Resolve filter options and expand directory paths.

    Validates mutual exclusion of --filter and --filter-type, resolves
    filter_type to glob pattern, and expands directories.

    Args:
        paths: List of input paths to process.
        filter_glob: Optional glob pattern from --filter option.
        filter_type: Optional filter type from --filter-type option.

    Returns:
        Tuple of (expanded_paths, is_batch).

    Raises:
        typer.Exit: On invalid filter options (exit code 2).
    """
    if filter_glob is not None and filter_type is not None:
        typer.echo("Error: --filter and --filter-type are mutually exclusive", err=True)
        raise typer.Exit(2) from None

    resolved_glob: str | None = filter_glob
    if filter_type is not None:
        if filter_type not in FILTER_TYPE_MAP:
            valid = ", ".join(FILTER_TYPE_MAP)
            typer.echo(f"Error: --filter-type must be one of: {valid}", err=True)
            raise typer.Exit(2) from None
        resolved_glob = FILTER_TYPE_MAP[filter_type]

    expanded_paths: list[Path] = []
    is_batch = False
    for path in paths:
        if resolved_glob is not None and path.is_dir():
            matched = sorted(path.glob(resolved_glob))
            expanded_paths.extend(matched)
            is_batch = True
        elif resolved_glob is None and path.is_dir():
            # Use discovery mode to determine scan targets
            discovery_mode = detect_discovery_mode(path)

            if discovery_mode == ScanDiscoveryMode.MANIFEST:
                # Manifest-driven: use explicit component declarations
                manifest = read_plugin_manifest(path)
                if manifest:
                    expanded_paths.extend(get_manifest_discovery_paths(manifest))
                    is_batch = True

            elif discovery_mode == ScanDiscoveryMode.AUTO:
                # Auto-discovery: use DEFAULT_SCAN_PATTERNS
                expanded_paths.extend(discover_validatable_paths(path))
                is_batch = True

            elif discovery_mode == ScanDiscoveryMode.STRUCTURE:
                # Structure-based: use provider directory patterns
                expanded_paths.extend(get_structure_discovery_paths(path))
                is_batch = True

        else:
            expanded_paths.append(path)
    return expanded_paths, is_batch


def compute_summary(all_results: FileResults) -> tuple[int, int, int, int]:
    """Compute validation summary statistics from file results.

    Args:
        all_results: Mapping of file paths to validation results.

    Returns:
        Tuple of (total_files, passed, failed, warnings).
    """
    total_files = len(all_results)
    passed = sum(1 for vr_list in all_results.values() if all(r.passed for _, r in vr_list))
    failed = sum(1 for vr_list in all_results.values() if any(not r.passed for _, r in vr_list))
    warnings = sum(
        1
        for vr_list in all_results.values()
        if all(r.passed for _, r in vr_list) and any(r.warnings for _, r in vr_list)
    )
    return total_files, passed, failed, warnings


class ValidationLoopRunner(Protocol):
    """Protocol for validation loop execution.

    Allows different implementations to be injected for testing
    or platform-specific behavior.
    """

    def run(
        self,
        expanded_paths: list[Path],
        *,
        check: bool,
        fix: bool,
        verbose: bool,
        show_progress: bool,
        show_summary: bool,
    ) -> NoReturn:
        """Execute validation loop and exit.

        Args:
            expanded_paths: Resolved file paths to validate.
            check: Validate only, don't auto-fix.
            fix: Auto-fix issues where possible.
            verbose: Show detailed output.
            show_progress: Show per-file status.
            show_summary: Show summary panel.

        Raises:
            typer.Exit: Always exits with appropriate code.
        """
        ...


def run_validation_loop(
    *,
    expanded_paths: list[Path],
    validate_single_path: Callable[[Path, bool, bool, bool], FileResults],
    reporter: Reporter,
    verbose: bool,
    show_progress: bool,
    show_summary: bool,
    load_ignore_patterns: Callable[[], list[str]],
    is_ignored: Callable[[Path, list[str]], bool],
) -> NoReturn:
    """Execute the validation loop, report results, and exit.

    This is the core orchestration function that coordinates path iteration,
    validation dispatch, and result reporting. It accepts its dependencies
    as parameters to create a clean seam for testing and extension.

    Args:
        expanded_paths: Resolved file paths to validate.
        validate_single_path: Function to validate a single path.
        reporter: Reporter instance for output.
        verbose: Show detailed output.
        show_progress: Show per-file status.
        show_summary: Show summary panel.
        load_ignore_patterns: Function to load ignore patterns.
        is_ignored: Function to check if a path is ignored.

    Raises:
        typer.Exit: Always exits with appropriate code.
    """
    ignore_patterns = load_ignore_patterns()
    all_results: FileResults = {}

    for path in expanded_paths:
        if ignore_patterns and is_ignored(path, ignore_patterns):
            continue
        file_results = validate_single_path(path, check=True, fix=False, verbose=verbose)
        for file_path, validator_results in file_results.items():
            if file_path in all_results:
                all_results[file_path].extend(validator_results)
            else:
                all_results[file_path] = list(validator_results)

    reporter.report(all_results, verbose=verbose, show_progress=show_progress)

    total_files, passed, failed, warnings = compute_summary(all_results)
    if show_summary:
        reporter.summarize(total_files, passed, failed, warnings)

    if failed > 0:
        raise typer.Exit(1) from None
    raise typer.Exit(0) from None
