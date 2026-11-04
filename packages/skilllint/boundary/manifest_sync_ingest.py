"""Validate manifest shapes before preparing any synchronizer writes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


class _PluginDocument(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    name: str | None = None
    version: str = "0.0.0"
    skills: str | list[str] | None = None
    agents: str | list[str] | None = None
    commands: str | list[str] | None = None


class _MarketplaceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    version: str = "0.0.0"


class _MarketplacePlugin(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    name: str


class _MarketplaceDocument(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    metadata: _MarketplaceMetadata = Field(default_factory=_MarketplaceMetadata)
    plugins: list[_MarketplacePlugin] = Field(default_factory=list)


def decode_plugin_sync_document(content: bytes) -> dict[str, JsonValue]:
    """Validate sync fields while preserving every authored JSON field and value.

    Returns:
        The original decoded object, after validation of fields used by sync.
    """
    data = _JSON_OBJECT.validate_json(content, strict=True)
    _PluginDocument.model_validate(data)
    return data


def decode_marketplace_sync_document(content: bytes) -> dict[str, JsonValue]:
    """Validate marketplace structure without rewriting unrelated metadata.

    Returns:
        The original decoded object, after validation of fields used by sync.
    """
    data = _JSON_OBJECT.validate_json(content, strict=True)
    _MarketplaceDocument.model_validate(data)
    return data
