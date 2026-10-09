"""Scan expansion and validation-loop orchestration.

Extracted from ``plugin_validator`` so the CLI entrypoint can delegate
path discovery, filtering, ignore-pattern handling, and the main
validation loop to a dedicated module without changing user-facing behavior.
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, NoReturn

import typer
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .adapters import PlatformAdapter, PlatformPluginDiscovery, PluginLayout, matches_file
from .file_types import ScanContext
from .plugin_manifest import _load_plugin_json
from .reporting import CIReporter, ConsoleReporter, FileResults, Reporter

if TYPE_CHECKING:
    from rich.console import Console

    from .models import AppliedFix

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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
    "**/.claude-plugin/marketplace.json",
    # A Codex plugin manifest is its own target (not its root) so only the
    # PLUGIN validators that recognise .codex-plugin run on it (LK004).
    "**/.codex-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)


KNOWN_PROVIDER_DIRS: frozenset[str] = frozenset({".claude", ".cursor", ".gemini", ".codex"})

# Directory names skilllint never scans into during discovery. `.git` and
# `node_modules` are the client-implementation guide's explicit recommendation
# (agentskills.io/client-implementation/adding-skills-support); `.venv` is the
# same class of irrelevant/vendored tree and is not reliably covered by the
# separate gitignore-based filter in run_validation_loop (that filter only
# applies when a git repo is present at all).
EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules", ".venv"})

PLUGIN_FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "skills/*/SKILL.md",
    "agents": "agents/*.md",
    "commands": "commands/*.md",
}


# ---------------------------------------------------------------------------
# Plugin root anchors
# ---------------------------------------------------------------------------


def _find_anchor_dir(path: Path, marker_relpath: str) -> Path | None:
    """Walk upward from path looking for a marker relative to a root.

    Args:
        path: File or directory from which to start the ancestry walk.
        marker_relpath: Marker path relative to a candidate root.

    Returns:
        The nearest directory containing the marker, or None.
    """
    search_path = path.parent if path.is_file() else path
    for parent in [search_path, *search_path.parents]:
        if (parent / marker_relpath).exists():
            return parent
    return None


def find_plugin_dir(path: Path) -> Path | None:
    """Return the nearest Claude plugin root containing plugin.json."""
    return _find_anchor_dir(path, ".claude-plugin/plugin.json")


def find_marketplace_dir(path: Path) -> Path | None:
    """Return the nearest marketplace root containing marketplace.json."""
    return _find_anchor_dir(path, ".claude-plugin/marketplace.json")


# ---------------------------------------------------------------------------
# Plugin manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginManifest:
    """Parsed paths from plugin.json, if declared."""

    plugin_root: Path
    agents: list[str] | None = None
    commands: list[str] | None = None
    skills: list[str] | None = None

    @property
    def is_manifest_driven(self) -> bool:
        """True if plugin.json declares any explicit paths."""
        return any(v is not None for v in (self.agents, self.commands, self.skills))


def _parse_plugin_manifest(plugin_root: Path) -> PluginManifest:
    """Read plugin.json and extract declared paths.

    If plugin.json has no path declarations, all fields are None
    (convention-driven mode). Returns all-None manifest on error.

    Args:
        plugin_root: Directory containing .claude-plugin/plugin.json.

    Returns:
        PluginManifest with parsed paths or None fields.
    """
    raw = _load_plugin_json(plugin_root)
    if raw is None:
        return PluginManifest(plugin_root=plugin_root)

    def _extract(key: str) -> list[str] | None:
        value = raw.get(key)
        if isinstance(value, list) and all(isinstance(entry, str) for entry in value):
            return value
        return None

    return PluginManifest(
        plugin_root=plugin_root, agents=_extract("agents"), commands=_extract("commands"), skills=_extract("skills")
    )


def _discover_manifest_skill_paths(root: Path, paths: list[str]) -> set[Path]:
    discovered: dict[Path, Path] = {}
    for rel in paths:
        resolved = root / rel
        if not resolved.resolve().is_relative_to(root.resolve()):
            continue
        if resolved.is_dir():
            direct_skill = resolved / "SKILL.md"
            if direct_skill.is_file() and direct_skill.resolve().is_relative_to(root.resolve()):
                discovered.setdefault(_ignore_path(resolved), resolved)
            else:
                for child_skill in _glob_excluding(resolved, "*/SKILL.md"):
                    if child_skill.resolve().is_relative_to(root.resolve()):
                        discovered.setdefault(_ignore_path(child_skill), child_skill)
        elif resolved.is_file() and resolved.name == "SKILL.md":
            discovered.setdefault(_ignore_path(resolved), resolved)
    return set(discovered.values())


def _discover_plugin_paths(manifest: PluginManifest) -> list[Path]:
    """Discover validatable files in a plugin directory.

    Two modes based on manifest.is_manifest_driven:
    - Manifest-driven: Resolve exactly the declared paths. No globbing.
    - Convention-driven: Glob at plugin root only (no ** recursion).

    Never recurses into skills/*/agents/ or skills/*/commands/.

    In manifest-driven mode, existing declared paths are added. Missing entries
    remain the responsibility of root-level registration validation.
    Convention-driven mode uses glob matching so only existing files appear.

    Args:
        manifest: Parsed plugin manifest with plugin_root and path lists.

    Returns:
        Sorted list of unique paths.
    """
    discovered: set[Path] = set()
    root = manifest.plugin_root

    if manifest.skills is not None:
        discovered.update(_discover_manifest_skill_paths(root, manifest.skills))
    discovered.update(path.parent for path in _glob_excluding(root, "skills/*/SKILL.md"))

    for field, path_list in (("agents", manifest.agents), ("commands", manifest.commands)):
        if path_list is None:
            discovered.update(_glob_excluding(root, f"{field}/*.md"))
            continue
        for rel in path_list:
            resolved = root / rel
            if not resolved.resolve().is_relative_to(root.resolve()):
                continue
            if resolved.is_dir():
                discovered.update(
                    child
                    for child in _glob_excluding(resolved, "*.md")
                    if child.resolve().is_relative_to(root.resolve())
                )
            elif resolved.is_file() and resolved.suffix == ".md":
                discovered.add(resolved)

    discovered.add(root)

    if (root / "hooks" / "hooks.json").exists():
        discovered.add(root / "hooks" / "hooks.json")
    if (root / "CLAUDE.md").exists():
        discovered.add(root / "CLAUDE.md")

    return sorted(discovered)


# ---------------------------------------------------------------------------
# Scan context detection
# ---------------------------------------------------------------------------


def detect_scan_context(directory: Path) -> ScanContext:
    """Identify the scan context of a directory.

    Decision order:
    1. If directory contains .claude-plugin/plugin.json -> PLUGIN
    2. If directory name matches a known provider prefix (.claude, .cursor,
       .gemini, etc.) -> PROVIDER
    3. Otherwise -> BARE

    Plugin check takes precedence over provider check: a .claude/ directory
    that also contains .claude-plugin/plugin.json is classified as PLUGIN.

    Args:
        directory: The target directory to classify.

    Returns:
        ScanContext enum value.
    """
    if (directory / ".claude-plugin" / "plugin.json").exists():
        return ScanContext.PLUGIN
    if directory.name in KNOWN_PROVIDER_DIRS:
        return ScanContext.PROVIDER
    return ScanContext.BARE


def _is_skill_folder(path: Path) -> bool:
    """Return whether *path* is a standalone folder-backed skill target."""
    return path.is_dir() and (path / "SKILL.md").is_file()


def _is_within_excluded_dir(relative_path: Path) -> bool:
    """Return whether any component of *relative_path* is a directory skilllint skips.

    ``relative_path`` must already be relative to the directory being walked —
    checking components of an absolute/raw path would also match ancestor
    segments belonging to the scan root itself (e.g. a target explicitly
    named ``node_modules/my-plugin``), which is not what EXCLUDED_DIR_NAMES
    is for: it exists to avoid walking *into* a vendored tree during
    discovery, not to second-guess an explicitly named target.
    """
    return any(part in EXCLUDED_DIR_NAMES for part in relative_path.parts)


def _glob_excluding(directory: Path, pattern: str) -> list[Path]:
    """Glob *pattern* under *directory*, dropping matches under excluded dirs.

    Only path components discovered beneath *directory* are checked against
    EXCLUDED_DIR_NAMES, so an excluded name in the scan root's own ancestry
    does not suppress results.

    Returns:
        Matching paths, excluding any under a directory named in EXCLUDED_DIR_NAMES.
    """
    return [p for p in directory.glob(pattern) if not _is_within_excluded_dir(p.relative_to(directory))]


def _discover_provider_paths(directory: Path) -> list[Path]:
    """Discover validatable files in a provider directory.

    Uses the provider's known locations:
        {directory}/agents/**/*.md
        {directory}/skills/*/SKILL.md

    No other files in the provider tree are discovered as agents or skills.

    Args:
        directory: The provider directory (e.g., .claude/).

    Returns:
        Sorted list of unique paths.
    """
    discovered: set[Path] = set(_glob_excluding(directory, "agents/**/*.md"))
    discovered.update(path.parent for path in _glob_excluding(directory, "skills/*/SKILL.md"))
    return sorted(discovered)


def _discover_bare_paths(directory: Path) -> list[Path]:
    """Discover paths in a bare directory outside plugin/provider subtrees.

    Returns:
        Sorted validatable paths discovered outside nested plugin/provider roots.
    """
    discovered: set[Path] = set()
    plugin_roots: set[Path] = set()
    for plugin_json in _glob_excluding(directory, "**/.claude-plugin/plugin.json"):
        plugin_root = plugin_json.parent.parent
        plugin_roots.add(plugin_root)
        discovered.update(_discover_plugin_paths(_parse_plugin_manifest(plugin_root)))

    provider_roots: set[Path] = set()
    for provider_name in KNOWN_PROVIDER_DIRS:
        for provider_dir in _glob_excluding(directory, f"**/{provider_name}"):
            if not provider_dir.is_dir() or any(provider_dir.is_relative_to(root) for root in plugin_roots):
                continue
            provider_roots.add(provider_dir)
            discovered.update(_discover_provider_paths(provider_dir))

    covered_roots = plugin_roots | provider_roots
    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in _glob_excluding(directory, pattern):
            if ".claude-plugin/" in pattern:
                # Both plugin.json and marketplace.json anchor a root two
                # levels up from the match (skilllint#118).
                candidate = match.parent.parent
            elif pattern.endswith("skills/*/SKILL.md"):
                candidate = match.parent
            else:
                candidate = match
            if not any(candidate.is_relative_to(root) for root in covered_roots):
                discovered.add(candidate)
    return sorted(discovered)


# ---------------------------------------------------------------------------
# Path discovery and filtering
# ---------------------------------------------------------------------------


def _adapter_plugin_layouts(adapter: PlatformAdapter) -> tuple[PluginLayout, ...]:
    """Return optional plugin layouts without extending PlatformAdapter."""
    if isinstance(adapter, PlatformPluginDiscovery):
        return adapter.plugin_layouts()
    return ()


def _plugin_layout_matches(directory: Path, adapter: PlatformAdapter) -> list[tuple[Path, Path, PluginLayout]]:
    """Return (root, manifest, layout) triples owned by one adapter."""
    matches: list[tuple[Path, Path, PluginLayout]] = []
    for layout in _adapter_plugin_layouts(adapter):
        marker_parts = PurePath(layout.manifest_path).parts
        if not marker_parts:
            continue
        for manifest in _glob_excluding(directory, f"**/{layout.manifest_path}"):
            if not manifest.is_file():
                continue
            # Root plugin.json is the Agent Plugins portable manifest. A
            # provider overlay such as .claude-plugin/plugin.json or
            # .cursor-plugin/plugin.json is not another portable plugin rooted
            # inside that hidden metadata directory.
            if (
                marker_parts == ("plugin.json",)
                and manifest.parent.name.startswith(".")
                and manifest.parent.name.endswith("-plugin")
            ):
                continue
            root = manifest
            for _part in marker_parts:
                root = root.parent
            matches.append((root, manifest, layout))
    return matches


def _plugin_root_owners(directory: Path, adapters: Sequence[PlatformAdapter]) -> dict[Path, frozenset[str]]:
    """Map discovered plugin roots to every adapter that declares that layout.

    Returns:
        Plugin roots mapped to the adapter IDs that claim each root.
    """
    mutable: dict[Path, set[str]] = {}
    for adapter in adapters:
        for root, _manifest, _layout in _plugin_layout_matches(directory, adapter):
            mutable.setdefault(root, set()).add(adapter.id())
    return {root: frozenset(owners) for root, owners in mutable.items()}


def _nearest_plugin_root(candidate: Path, owners: dict[Path, frozenset[str]]) -> Path | None:
    """Return the deepest declared plugin root containing candidate."""
    roots = [root for root in owners if candidate == root or candidate.is_relative_to(root)]
    return max(roots, key=lambda root: len(root.parts)) if roots else None


def _platform_owns_candidate(candidate: Path, adapter: PlatformAdapter, owners: dict[Path, frozenset[str]]) -> bool:
    """Reject files inside a plugin root owned only by another platform.

    Returns:
        True when the candidate is unowned or owned by the selected adapter.
    """
    root = _nearest_plugin_root(candidate, owners)
    return root is None or adapter.id() in owners[root]


def _platform_plugin_targets(directory: Path, adapter: PlatformAdapter) -> set[Path]:
    """Return adapter-declared plugin validation targets under directory."""
    targets: set[Path] = set()
    for root, manifest, layout in _plugin_layout_matches(directory, adapter):
        if layout.validation_target == "root":
            targets.add(root)
        elif layout.validation_target == "manifest":
            targets.add(manifest)
    return targets


def _discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files using context-appropriate rules.

    Detects the scan context of the directory and dispatches to the
    appropriate discovery function:
    - PLUGIN: parse manifest and discover plugin-scoped paths
    - PROVIDER: discover agents/**/*.md only
    - BARE: handle nested plugins and providers, then apply DEFAULT_SCAN_PATTERNS
             for paths not covered by any plugin/provider subtree

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    context = detect_scan_context(directory)

    if context == ScanContext.PLUGIN:
        manifest = _parse_plugin_manifest(directory)
        return _discover_plugin_paths(manifest)

    if context == ScanContext.PROVIDER:
        return _discover_provider_paths(directory)

    if _is_skill_folder(directory):
        return [directory]

    return _discover_bare_paths(directory)


def _platform_matching_paths(
    paths: list[Path],
    directory: Path,
    adapter: PlatformAdapter | None,
    platform_adapters: Sequence[PlatformAdapter] | None = None,
) -> list[Path]:
    if adapter is None:
        return paths

    adapter_universe = tuple(platform_adapters) if platform_adapters is not None else (adapter,)
    plugin_owners = _plugin_root_owners(directory, adapter_universe)
    semantic_targets = sorted(_discover_validatable_paths(directory), key=lambda path: len(path.parts), reverse=True)
    matched = [
        path
        for path in paths
        if path.is_file()
        and _platform_owns_candidate(path, adapter, plugin_owners)
        and not (adapter.id() == "claude_code" and _is_foreign_provider_target(path, directory))
        and (
            _matches_platform_path(adapter, path, directory)
            or (
                adapter.id() == "claude_code"
                and any(
                    (target.is_file() or _is_skill_folder(target) or _is_claude_marketplace_root(target))
                    and (path == target or path.is_relative_to(target))
                    for target in semantic_targets
                )
            )
        )
    ]
    return sorted({_semantic_platform_target(path, semantic_targets, adapter) for path in matched})


def _matches_platform_path(adapter: PlatformAdapter, candidate: Path, directory: Path) -> bool:
    relative_candidate = candidate.relative_to(directory)
    if _matches_platform_relative_path(adapter, relative_candidate):
        return True
    return any(
        _matches_platform_relative_path(adapter, candidate.relative_to(ancestor.parent))
        for ancestor in (directory, *directory.parents)
    )


def _matches_platform_relative_path(adapter: PlatformAdapter, candidate: Path) -> bool:
    if matches_file(adapter, candidate):
        return True
    return any(
        pattern.startswith("**/") and candidate.match(pattern.removeprefix("**/"))
        for pattern in adapter.path_patterns()
    )


def _plugin_manifest_target(candidate: Path, adapter: PlatformAdapter) -> Path | None:
    """Normalize an adapter-declared manifest to its validation target.

    Returns:
        The declared root/manifest target, or None when candidate is not one.
    """
    for layout in _adapter_plugin_layouts(adapter):
        marker_parts = PurePath(layout.manifest_path).parts
        if not marker_parts or tuple(candidate.parts[-len(marker_parts) :]) != marker_parts:
            continue
        root = candidate
        for _part in marker_parts:
            root = root.parent
        if layout.validation_target == "root":
            return root
        if layout.validation_target == "manifest":
            return candidate
    return None


def _semantic_platform_target(candidate: Path, semantic_targets: list[Path], adapter: PlatformAdapter) -> Path:
    if (plugin_target := _plugin_manifest_target(candidate, adapter)) is not None:
        return plugin_target
    if adapter.id() not in {"claude_code", "codex", "cursor"}:
        return candidate
    if adapter.id() == "codex" and candidate.name == "AGENTS.md":
        return candidate
    if adapter.id() == "claude_code":
        marketplace_root = next(
            (
                semantic_target
                for semantic_target in semantic_targets
                if _is_claude_marketplace_root(semantic_target)
                and candidate == semantic_target / ".claude-plugin" / "marketplace.json"
            ),
            None,
        )
        if marketplace_root is not None:
            return marketplace_root
    if candidate.suffix != ".md":
        return candidate
    return next(
        (
            semantic_target
            for semantic_target in semantic_targets
            if candidate == semantic_target or candidate.is_relative_to(semantic_target)
            if not (semantic_target / ".claude-plugin" / "plugin.json").is_file()
        ),
        candidate,
    )


def _is_manifest_declared_target(target: Path, directory: Path) -> bool:
    for plugin_root in target.parents:
        if plugin_root != directory and not plugin_root.is_relative_to(directory):
            break
        if not (plugin_root / ".claude-plugin" / "plugin.json").is_file():
            continue
        manifest = _parse_plugin_manifest(plugin_root)
        return manifest.is_manifest_driven and target in _discover_plugin_paths(manifest)
    return False


def _manifest_filter_type_is_malformed(raw_manifest: dict | None, filter_type: str) -> bool:
    if raw_manifest is None:
        return True
    if filter_type not in raw_manifest:
        return False
    declared_paths = raw_manifest[filter_type]
    return not isinstance(declared_paths, list) or any(not isinstance(path, str) for path in declared_paths)


def _manifest_filter_type_paths(
    directory: Path, filter_type: str | None, adapter: PlatformAdapter | None
) -> list[Path]:
    if adapter is None or adapter.id() != "claude_code" or detect_scan_context(directory) != ScanContext.PLUGIN:
        return []
    manifest = _parse_plugin_manifest(directory)
    manifest_path = directory / ".claude-plugin" / "plugin.json"
    raw_manifest = _load_plugin_json(directory)
    match filter_type:
        case "agents":
            declared_paths = manifest.agents
        case "commands":
            declared_paths = manifest.commands
        case "skills":
            declared_paths = manifest.skills
        case _:
            return []
    if _manifest_filter_type_is_malformed(raw_manifest, filter_type):
        return [manifest_path]
    declared_paths = declared_paths or []
    targets: list[Path] = []
    directory_root = directory.resolve()
    for declared_path in declared_paths:
        target = directory / declared_path
        if not target.resolve().is_relative_to(directory_root):
            continue
        if _is_foreign_provider_target(target, directory):
            continue
        if not target.exists():
            target = directory / ".claude-plugin" / "plugin.json"
        if target.is_dir() and filter_type in {"agents", "commands"}:
            targets.extend(
                child for child in _glob_excluding(target, "*.md") if child.resolve().is_relative_to(directory_root)
            )
            continue
        if filter_type == "skills" and not (
            _is_skill_folder(target) or (target.is_file() and target.name == "SKILL.md")
        ):
            target = directory / ".claude-plugin" / "plugin.json"
        targets.append(target)
    return targets


def _is_claude_marketplace_root(target: Path) -> bool:
    return (target / ".claude-plugin" / "marketplace.json").is_file()


def _is_foreign_provider_target(target: Path, directory: Path) -> bool:
    foreign_provider_roots = (KNOWN_PROVIDER_DIRS | {".agents"}) - {".claude"}
    return any(
        ancestor.name in foreign_provider_roots
        for ancestor in (target, *target.parents)
        if ancestor == directory or ancestor.is_relative_to(directory)
    )


def _matches_semantic_target(adapter: PlatformAdapter, target: Path, directory: Path) -> bool:
    if _is_foreign_provider_target(target, directory):
        return False
    if (target / ".claude-plugin" / "plugin.json").is_file() or _is_claude_marketplace_root(target):
        return True
    if _is_manifest_declared_target(target, directory):
        return True
    if target.is_dir():
        return _is_skill_folder(target)
    relative_target = target.relative_to(directory)
    return _matches_platform_path(adapter, target, directory) or (
        target.suffix == ".md"
        and (target.name == "CLAUDE.md" or any(part in {"agents", "commands"} for part in relative_target.parts))
    )


def _discover_platform_paths(
    directory: Path, adapter: PlatformAdapter, platform_adapters: Sequence[PlatformAdapter] | None = None
) -> list[Path]:
    adapter_universe = tuple(platform_adapters) if platform_adapters is not None else (adapter,)
    plugin_owners = _plugin_root_owners(directory, adapter_universe)

    if adapter.id() == "claude_code":
        return [
            target
            for target in _discover_validatable_paths(directory)
            if _platform_owns_candidate(target, adapter, plugin_owners)
            and _matches_semantic_target(adapter, target, directory)
        ]

    semantic_targets = sorted(_discover_validatable_paths(directory), key=lambda path: len(path.parts), reverse=True)
    discovered = _platform_plugin_targets(directory, adapter)
    for candidate in _glob_excluding(directory, "**/*"):
        if (
            not candidate.is_file()
            or not _platform_owns_candidate(candidate, adapter, plugin_owners)
            or not _matches_platform_path(adapter, candidate, directory)
        ):
            continue
        discovered.add(_semantic_platform_target(candidate, semantic_targets, adapter))
    return sorted(discovered)


def _validate_filter_options(filter_glob: str | None, filter_type: str | None) -> None:
    if filter_glob is not None and filter_type is not None:
        typer.echo("Error: --filter and --filter-type are mutually exclusive", err=True)
        raise typer.Exit(2) from None

    if filter_type is not None and filter_type not in FILTER_TYPE_MAP:
        valid = ", ".join(FILTER_TYPE_MAP)
        typer.echo(f"Error: --filter-type must be one of: {valid}", err=True)
        raise typer.Exit(2) from None


def _resolve_filter_and_expand_paths(
    paths: list[Path],
    filter_glob: str | None,
    filter_type: str | None,
    *,
    platform_adapter: PlatformAdapter | None = None,
    platform_adapters: Sequence[PlatformAdapter] | None = None,
) -> tuple[list[Path], bool]:
    """Resolve filter options and expand directory paths.

    Validates mutual exclusion of --filter and --filter-type, resolves
    filter_type to glob pattern, and expands directories.

    Returns:
        Tuple of (expanded_paths, is_batch).

    Raises:
        typer.Exit: On invalid filter options.
    """
    _validate_filter_options(filter_glob, filter_type)

    expanded_paths: list[Path] = []
    is_batch = False
    for path in paths:
        if filter_type is not None:
            # Context-aware resolution: plugin dirs use root-only globs to
            # avoid matching skill-internal agent/command files.
            if path.is_dir() and detect_scan_context(path) == ScanContext.PLUGIN:
                resolved_glob: str | None = PLUGIN_FILTER_TYPE_MAP.get(filter_type, FILTER_TYPE_MAP[filter_type])
            else:
                resolved_glob = FILTER_TYPE_MAP[filter_type]
        else:
            resolved_glob = filter_glob
        if resolved_glob is not None and path.is_dir():
            matched = _glob_excluding(path, resolved_glob)
            matched = _platform_matching_paths(matched, path, platform_adapter, platform_adapters)
            matched.extend(_manifest_filter_type_paths(path, filter_type, platform_adapter))
            if filter_type == "skills" and platform_adapter is None:
                matched = [match.parent for match in matched]
            expanded_paths.extend(matched)
            is_batch = True
        elif resolved_glob is None and path.is_dir():
            if platform_adapter is None:
                expanded_paths.extend(_discover_validatable_paths(path))
            else:
                expanded_paths.extend(_discover_platform_paths(path, platform_adapter, platform_adapters))
            is_batch = True
        else:
            expanded_paths.append(path)
    if platform_adapter is None:
        return expanded_paths, is_batch
    return list(dict.fromkeys(expanded_paths)), is_batch


# ---------------------------------------------------------------------------
# Ignore patterns
# ---------------------------------------------------------------------------


def _build_gitignore_set(paths: Sequence[Path], scan_base: Path | None) -> frozenset[str]:
    """Return the set of absolute path strings that git considers ignored.

    Calls repo.ignored() once for all paths rather than once per file.
    Returns an empty frozenset when no git repo is found or paths is empty.

    Args:
        paths: Paths to test against git's ignore rules.
        scan_base: Directory used to locate the governing git repo. Evaluating
            from the scan base is important when scanning an external directory:
            files inside git worktrees nested under the scan root would otherwise
            resolve to their own repo, bypassing the parent repo's .gitignore rules.

    Returns:
        Frozenset of resolved absolute path strings that git would ignore.
    """
    if not paths or scan_base is None:
        return frozenset()
    anchor = scan_base
    try:
        repo = Repo(anchor, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return frozenset()
    ignored = repo.ignored(*[str(p.resolve()) for p in paths])
    return frozenset(str(Path(p).resolve()) for p in ignored)


def _load_ignore_patterns() -> list[str]:
    """Load glob patterns from .pluginvalidatorignore file.

    Searches for the ignore file in the following order:
    1. Current working directory (.pluginvalidatorignore)
    2. .claude/.pluginvalidatorignore

    Each line is a gitignore-style glob pattern. Lines starting with '#' are
    comments, blank lines are ignored.

    Returns:
        List of glob patterns to match against file paths.
    """
    candidates = [Path.cwd() / ".pluginvalidatorignore", Path.cwd() / ".claude" / ".pluginvalidatorignore"]
    for candidate in candidates:
        if candidate.is_file():
            lines = candidate.read_text(encoding="utf-8").splitlines()
            return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return []


def _is_ignored(path: Path, patterns: list[str]) -> bool:
    """Check whether a path matches any ignore pattern.

    Patterns follow gitignore-style glob semantics:
    - ``**/templates/*.md`` matches any ``templates`` directory at any depth
    - ``plugins/foo/bar.md`` matches that exact relative path

    The path is tested as a POSIX string (forward slashes) so patterns work
    consistently across platforms.

    Args:
        path: File path to check (absolute or relative).
        patterns: Glob patterns loaded from .pluginvalidatorignore.

    Returns:
        True if the path matches any pattern and should be skipped.
    """
    path_str = path.as_posix()
    resolved_path = path.resolve()
    cwd = Path.cwd().resolve()
    for pattern in patterns:
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # Also match against just the relative-to-cwd representation
        try:
            rel = resolved_path.relative_to(cwd).as_posix()
        except ValueError:
            rel = path_str
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def _compute_summary(all_results: FileResults) -> tuple[int, int, int, int]:
    """Compute validation summary statistics from file results.

    Returns:
        Tuple of (total_files, passed, failed, warnings).
    """
    total_files = len(all_results)
    passed = 0
    failed = 0
    warnings = 0
    for vr_list in all_results.values():
        all_passed = all(r.passed for _, r in vr_list)
        if all_passed:
            passed += 1
            if any(r.warnings for _, r in vr_list):
                warnings += 1
        else:
            failed += 1
    return total_files, passed, failed, warnings


def _compute_scan_base(paths: list[Path]) -> Path | None:
    """Return the common ancestor directory of *paths* for gitignore evaluation.

    Gitignore rules must be evaluated from the perspective of the repo that
    owns the scan root, not from inside each individual file's own repo.  This
    matters when the scan root contains git worktrees: a file inside a worktree
    would otherwise resolve to the worktree's repo and miss the parent repo's
    ``.gitignore`` entries (e.g. ``.claude/worktrees/``).

    Args:
        paths: Expanded list of paths to be scanned.

    Returns:
        The common ancestor path, or None when *paths* is empty.
    """
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]

    return Path(os.path.commonpath(paths))


# ---------------------------------------------------------------------------
# Validation loop
# ---------------------------------------------------------------------------

# Callback type aliases for dependency injection from plugin_validator.
# This avoids circular imports: plugin_validator imports scan_runtime,
# and passes its own functions as callbacks when calling run_validation_loop.
ValidateSinglePathFn = Callable[..., "FileResults"]
ValidateFileFn = Callable[[Path, dict[str, PlatformAdapter], str | None], list[dict]]
ViolationsToResultFn = Callable[[list[dict]], Any]


def _ignore_path(path: Path) -> Path:
    """Return the concrete skill file for ignore matching when applicable."""
    skill_file = path / "SKILL.md"
    return skill_file if path.is_dir() and skill_file.is_file() else path


def _select_reporter(*, no_color: bool, record_console: Console | None) -> Reporter:
    """Choose the reporter implementation for this run.

    Args:
        no_color: Disable color output (selects the plain-text CI reporter).
        record_console: When provided, takes precedence so recorded output
            (e.g. SVG/HTML export) always uses Rich formatting.

    Returns:
        A ConsoleReporter (recording or colored) or a CIReporter.
    """
    if record_console is not None:
        return ConsoleReporter(console=record_console)
    if no_color:
        return CIReporter()
    return ConsoleReporter(no_color=no_color)


@dataclass(frozen=True)
class CheckRun:
    """What one scan produced, before anything is reported.

    Attributes:
        results: Validator results per file, in scan order.
        fixes: Fixes ``--fix`` applied, in the order they were recorded.
    """

    results: FileResults
    fixes: list[AppliedFix]


def collect_validation_results(
    *,
    expanded_paths: list[Path],
    check: bool,
    fix: bool,
    verbose: bool,
    platform_override: str | None,
    validate_single_path: ValidateSinglePathFn,
    validate_file: ValidateFileFn,
    violations_to_result: ViolationsToResultFn,
    adapters: dict[str, PlatformAdapter],
    include_gitignore: bool = False,
) -> CheckRun:
    """Validate every path that is not ignored and gather the results.

    Dependencies from ``plugin_validator`` are injected as callbacks to
    avoid circular imports at module level.

    Args:
        expanded_paths: Resolved file paths to validate.
        check: Validate only, don't auto-fix.
        fix: Auto-fix issues where possible.
        verbose: Show detailed output.
        platform_override: Restrict to this adapter ID.
        validate_single_path: Callback to validate a single path.
        validate_file: Callback to validate a file with platform adapters.
        violations_to_result: Callback to convert violations to ValidationResult.
        adapters: Platform adapter registry dict.
        include_gitignore: When False (default), paths excluded by git's ignore
            rules are skipped. When True, gitignored paths are included.

    Returns:
        The results and the fixes applied.
    """
    ignore_patterns = _load_ignore_patterns()

    scan_base = _compute_scan_base(expanded_paths)

    ignored_set: frozenset[str] = (
        _build_gitignore_set([_ignore_path(path) for path in expanded_paths], scan_base)
        if not include_gitignore
        else frozenset()
    )

    def _should_skip(p: Path) -> bool:
        if ignore_patterns and _is_ignored(p, ignore_patterns):
            return True
        return str(p.resolve()) in ignored_set

    all_results: FileResults = {}
    all_fixes: list[AppliedFix] = []
    # Folders --fix renamed during this run (old -> new). Paths queued under an old folder follow it.
    moved_folders: dict[Path, Path] = {}
    for queued in expanded_paths:
        path = _follow_moved_folders(queued, moved_folders)
        # The gitignore set was built from the paths as discovered, before any folder moved.
        if _should_skip(_ignore_path(queued)) or _should_skip(_ignore_path(path)):
            continue
        if platform_override is not None:
            violations = validate_file(_ignore_path(path), adapters, platform_override)
            all_results[path] = [("platform", violations_to_result(violations))]
        else:
            was_dir = path.is_dir()
            file_results = validate_single_path(path, check=check, fix=fix, verbose=verbose, fixes_out=all_fixes)
            if fix:
                for file_path in file_results:
                    if (move := _folder_move(path, file_path, was_dir=was_dir)) is not None:
                        moved_folders[move[0]] = move[1]
                        _rebase_collected(all_results, all_fixes, *move)
            for file_path, validator_results in file_results.items():
                if file_path in all_results:
                    all_results[file_path].extend(validator_results)
                else:
                    all_results[file_path] = list(validator_results)

    return CheckRun(results=all_results, fixes=all_fixes)


def _folder_move(queued: Path, result: Path, *, was_dir: bool) -> tuple[Path, Path] | None:
    """Return ``(old, new)`` when validating *queued* renamed its skill folder, else None.

    *queued* is the folder or a file directly in it (*was_dir* says which, as checked before
    validation). The folder moved when the result's folder sits beside it under another spelling.
    Spellings are compared as strings because Windows paths compare equal across a case-only rename.

    Returns:
        The old and new folder, or None when the folder kept its name.
    """
    folder = queued if was_dir else queued.parent
    moved_to = result.parent
    if str(result) == str(queued) or str(moved_to) == str(folder) or str(moved_to.parent) != str(folder.parent):
        return None
    return folder, moved_to


def _rebased(path: Path, old: Path, new: Path) -> Path | None:
    """Return *path* moved from under *old* to under *new*, or None when it is not under *old*.

    Compares spellings as strings: ``Path.is_relative_to`` is too slow to call for every collected
    path on every rename of a large --fix run, and a string match also keeps case-only renames apart.
    """
    text, prefix = str(path), str(old)
    if text == prefix:
        return new
    if text.startswith(prefix + os.sep):
        return new / text[len(prefix) + 1 :]
    return None


def _rebase_collected(results: FileResults, fixes: list[AppliedFix], old: Path, new: Path) -> None:
    """Move results and fixes already collected under *old* to *new*, in place.

    Paths listed before the skill that renamed their folder were recorded under the old spelling.
    """
    for key in list(results):
        if (moved := _rebased(key, old, new)) is not None:
            results[moved] = results.pop(key)
    for index, fix in enumerate(fixes):
        if (moved := _rebased(fix.path, old, new)) is not None:
            fixes[index] = replace(fix, path=moved)


def _follow_moved_folders(path: Path, moved_folders: dict[Path, Path]) -> Path:
    """Return where *path* is now, given the folders renamed earlier in the run.

    Moves are applied in the order they happened, so a rename inside an already renamed folder
    (recorded against the folder's new name) is followed too.

    Returns:
        *path* rebased onto every renamed folder it lay under, otherwise *path*.
    """
    for old, new in moved_folders.items():
        if (moved := _rebased(path, old, new)) is not None:
            path = moved
    return path


def report_results(
    run: CheckRun,
    *,
    verbose: bool,
    no_color: bool,
    show_progress: bool,
    show_summary: bool,
    record_console: Console | None = None,
) -> int:
    """Render a scan with the selected reporter, as ``check`` prints it.

    Args:
        run: The scan to report.
        verbose: Show detailed output.
        no_color: Disable color output.
        show_progress: Show per-file status.
        show_summary: Show summary panel.
        record_console: When provided, pass this Rich Console to ConsoleReporter
            so its output is captured for export (e.g. SVG/HTML recording).

    Returns:
        The number of files that failed.
    """
    reporter = _select_reporter(no_color=no_color, record_console=record_console)
    reporter.report(run.results, verbose=verbose, show_progress=show_progress)
    if run.fixes:
        # Printed before summarize(): ConsoleReporter.summarize() mutates
        # self.console.width to fit its summary panel, so anything printed
        # afterwards on the same console would inherit that narrowed width.
        reporter.report_fixes(run.fixes)

    total_files, passed, failed, warnings = _compute_summary(run.results)
    if show_summary:
        reporter.summarize(total_files, passed, failed, warnings)
    return failed


def run_validation_loop(
    *,
    expanded_paths: list[Path],
    check: bool,
    fix: bool,
    verbose: bool,
    no_color: bool,
    show_progress: bool,
    show_summary: bool,
    platform_override: str | None,
    validate_single_path: ValidateSinglePathFn,
    validate_file: ValidateFileFn,
    violations_to_result: ViolationsToResultFn,
    adapters: dict[str, PlatformAdapter],
    record_console: Console | None = None,
    include_gitignore: bool = False,
) -> NoReturn:
    """Execute the validation loop, report results, and exit.

    Dependencies from ``plugin_validator`` are injected as callbacks to
    avoid circular imports at module level.

    Args:
        expanded_paths: Resolved file paths to validate.
        check: Validate only, don't auto-fix.
        fix: Auto-fix issues where possible.
        verbose: Show detailed output.
        no_color: Disable color output.
        show_progress: Show per-file status.
        show_summary: Show summary panel.
        platform_override: Restrict to this adapter ID.
        validate_single_path: Callback to validate a single path.
        validate_file: Callback to validate a file with platform adapters.
        violations_to_result: Callback to convert violations to ValidationResult.
        adapters: Platform adapter registry dict.
        record_console: When provided, pass this Rich Console to ConsoleReporter
            so its output is captured for export (e.g. SVG/HTML recording).
        include_gitignore: When False (default), paths excluded by git's ignore
            rules are skipped. When True, gitignored paths are included.

    Raises:
        typer.Exit: Always exits with appropriate code.
    """
    run = collect_validation_results(
        expanded_paths=expanded_paths,
        check=check,
        fix=fix,
        verbose=verbose,
        platform_override=platform_override,
        validate_single_path=validate_single_path,
        validate_file=validate_file,
        violations_to_result=violations_to_result,
        adapters=adapters,
        include_gitignore=include_gitignore,
    )
    failed = report_results(
        run,
        verbose=verbose,
        no_color=no_color,
        show_progress=show_progress,
        show_summary=show_summary,
        record_console=record_console,
    )

    if failed > 0:
        raise typer.Exit(1) from None
    raise typer.Exit(0) from None
