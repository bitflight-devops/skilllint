"""Platform adapter contracts.

The core PlatformAdapter protocol stays deliberately small so existing
third-party adapters remain structurally compatible. Optional discovery
capabilities are separate protocols: adapters opt in without making a new
method mandatory for every extension.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pathlib


ALL_RULE_SERIES = "*"
"""applicable_rules() sentinel for every rule series applicable to a platform."""


@dataclass(frozen=True)
class PluginLayout:
    """A manifest location that identifies a platform-owned plugin root.

    manifest_path is relative to the plugin root. validation_target describes
    which object explicit-platform discovery should validate when it finds that
    manifest. None means the manifest only scopes ownership of files below the
    plugin root.
    """

    manifest_path: str
    validation_target: Literal["root", "manifest"] | None = None


@runtime_checkable
class PlatformPluginDiscovery(Protocol):
    """Optional explicit-platform plugin discovery capability."""

    def plugin_layouts(self) -> tuple[PluginLayout, ...]:
        """Return plugin-root layouts recognized by this adapter."""
        ...


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for platform-specific skill/plugin adapters.

    Any class implementing all five methods satisfies this Protocol.
    No inheritance required — structural subtyping only.
    """

    def id(self) -> str:
        """Return the unique platform identifier (e.g. 'claude_code', 'cursor')."""
        ...

    def path_patterns(self) -> list[str]:
        """Return glob patterns matching files this adapter handles."""
        ...

    def applicable_rules(self) -> set[str]:
        """Return rule-series codes the explicit-platform runtime may emit.

        The declaration is an allow-list consumed by routing. A series entry
        such as "LK" permits registered LK rules whose rule-level platforms
        metadata also applies to this adapter. ALL_RULE_SERIES means every
        registered series applicable to the adapter; it does not bypass
        per-rule platform metadata.

        Third-party rule codes that are not in the core registry are governed
        by this series declaration alone.
        """
        ...

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        Values are extracted from field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').
        """
        ...

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate the given file path and return a list of violation dicts."""
        ...
