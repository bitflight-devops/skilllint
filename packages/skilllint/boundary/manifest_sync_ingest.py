"""Validate manifest shapes before preparing any synchronizer writes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class PluginSyncDocument(BaseModel):
    """Plugin fields used by sync, with unrelated authored JSON retained."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str | None = None
    version: str = "0.0.0"
    skills: str | list[str] | None = None
    agents: str | list[str] | None = None
    commands: str | list[str] | None = None

    def component_declarations(self) -> dict[str, str | list[str] | None]:
        """Return only authored component fields for registration updates."""
        fields = {"skills": self.skills, "agents": self.agents, "commands": self.commands}
        return {name: value for name, value in fields.items() if name in self.model_fields_set}

    def apply_component_declarations(self, fields: dict[str, str | list[str] | None]) -> None:
        """Apply component changes without materializing absent defaults."""
        if "skills" in fields:
            self.skills = fields["skills"]
        if "agents" in fields:
            self.agents = fields["agents"]
        if "commands" in fields:
            self.commands = fields["commands"]


class MarketplaceSyncMetadata(BaseModel):
    """Marketplace version and unrelated authored metadata."""

    model_config = ConfigDict(extra="allow", strict=True)

    version: str = "0.0.0"


class MarketplaceSyncPlugin(BaseModel):
    """A named marketplace registration with its authored extension fields."""

    model_config = ConfigDict(extra="allow", strict=True)

    name: str
    source: JsonValue = None


class MarketplaceSyncDocument(BaseModel):
    """Validated marketplace fields used when preparing a synchronization."""

    model_config = ConfigDict(extra="allow", strict=True)

    metadata: MarketplaceSyncMetadata = Field(default_factory=MarketplaceSyncMetadata)
    plugins: list[MarketplaceSyncPlugin] = Field(default_factory=list)


def decode_plugin_sync_document(content: bytes) -> PluginSyncDocument:
    """Return validated plugin fields, extras, and authored field presence."""
    return PluginSyncDocument.model_validate_json(content)


def decode_marketplace_sync_document(content: bytes) -> MarketplaceSyncDocument:
    """Return validated marketplace fields without exposing a raw payload."""
    return MarketplaceSyncDocument.model_validate_json(content)
