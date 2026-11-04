"""Normalize plugin component declarations and resolve their filesystem targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import JsonValue, TypeAdapter, ValidationError

ComponentKind = Literal["skills", "agents", "commands"]
_COMPONENT_FIELD = TypeAdapter(str | list[JsonValue])


@dataclass(frozen=True)
class ResolvedComponent:
    """Validity and scan targets for one declaration, including empty directories."""

    valid: bool
    paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ComponentReference:
    """An authored path, preserved separately from its resolved scan targets."""

    path: str

    @property
    def relative_path(self) -> Path:
        """The lexical path used in registration diagnostics."""
        return Path(self.path.removeprefix("./"))

    def resolve_target(self, plugin_dir: Path) -> Path | None:
        """Resolve parent traversals without losing subsequent lexical aliases.

        Returns:
            A contained target path, or None for an out-of-plugin reference.
        """
        target = plugin_dir / self.relative_path
        root = plugin_dir.resolve()
        if not target.resolve().is_relative_to(root):
            return None
        parts = self.relative_path.parts
        if ".." in parts:
            prefix_length = len(parts) - parts[::-1].index("..")
            prefix = (plugin_dir / Path(*parts[:prefix_length])).resolve()
            if prefix.is_relative_to(root):
                target = plugin_dir / prefix.relative_to(root) / Path(*parts[prefix_length:])
        return target

    def resolve(self, plugin_dir: Path, kind: ComponentKind) -> ResolvedComponent:
        """Resolve only valid capability targets contained inside the plugin.

        Returns:
            Target validity and lexical scan paths for this component kind.
        """
        target = self.resolve_target(plugin_dir)
        if target is None:
            return ResolvedComponent(False)
        root = plugin_dir.resolve()
        if target.is_file():
            valid = target.name == "SKILL.md" if kind == "skills" else target.suffix == ".md"
            return ResolvedComponent(valid, (target,) if valid else ())
        if kind == "skills":
            if target.is_dir():
                direct = target / "SKILL.md"
                if direct.is_file() and direct.resolve().is_relative_to(root):
                    return ResolvedComponent(True, (target,))
                children = tuple(
                    child
                    for child in sorted(target.glob("*/SKILL.md"))
                    if child.is_file() and child.resolve().is_relative_to(root)
                )
                return ResolvedComponent(bool(children), children)
        elif target.is_dir():
            children = tuple(
                child
                for child in sorted(target.glob("*.md"))
                if child.is_file() and child.resolve().is_relative_to(root)
            )
            return ResolvedComponent(True, children)
        return ResolvedComponent(False)


def component_references_from_raw(value: object) -> tuple[ComponentReference, ...] | None:
    """Normalize a scalar/list declaration without coercing invalid items to paths.

    Missing or malformed fields return None. Malformed list members remain the
    manifest validator's responsibility; valid string members can still be scanned.

    Returns:
        Authored path references, or None when no declaration can be ingested.
    """
    try:
        parsed = _COMPONENT_FIELD.validate_python(value, strict=True)
    except ValidationError:
        return None
    items = [parsed] if isinstance(parsed, str) else parsed
    return tuple(ComponentReference(item) for item in items if isinstance(item, str) and "\x00" not in item)
