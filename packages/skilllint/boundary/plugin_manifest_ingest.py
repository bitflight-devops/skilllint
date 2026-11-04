"""Read plugin manifests as strict JSON objects before PL rules inspect fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import msgspec.json
from pydantic import JsonValue, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from pathlib import Path

_JSON_OBJECT: TypeAdapter[dict[str, JsonValue]] = TypeAdapter(dict[str, JsonValue])


@dataclass(frozen=True, slots=True)
class PluginManifestDefect:
    """A read, syntax, or root-shape failure for the PL rules to describe."""

    kind: Literal["read", "syntax", "shape"]
    detail: str = ""


def ingest_plugin_manifest(path: Path) -> dict[str, JsonValue] | PluginManifestDefect:
    """Return an object-shaped manifest or the reason ingestion failed.

    Nested fields remain JSON values so their owning rules can report invalid
    values without rejecting the entire document at the ingestion boundary.

    Returns:
        A validated JSON object or a structured ingestion failure.
    """
    try:
        raw = msgspec.json.decode(path.read_bytes())
    except OSError as exc:
        return PluginManifestDefect("read", str(exc))
    except msgspec.DecodeError as exc:
        return PluginManifestDefect("syntax", str(exc))
    try:
        return _JSON_OBJECT.validate_python(raw, strict=True)
    except ValidationError:
        return PluginManifestDefect("shape")
