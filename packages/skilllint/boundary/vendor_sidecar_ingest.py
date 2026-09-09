"""Typed ingress for cached-document sidecar metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_serializer, field_validator


class SidecarMetadata(BaseModel):
    """Validated metadata stored beside a cached vendor document."""

    model_config = ConfigDict(frozen=True, strict=True)

    url: str
    fetched_at: datetime
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_count: int

    @field_validator("fetched_at")
    @classmethod
    def fetched_at_must_be_aware(cls, value: datetime) -> datetime:
        """Reject naive timestamps before cache freshness arithmetic.

        Returns:
            The validated aware timestamp.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must include a timezone")
        return value

    @field_serializer("fetched_at")
    def serialize_fetched_at(self, value: datetime) -> str:
        """Preserve the sidecar's ISO 8601 UTC offset representation.

        Returns:
            The offset-preserving timestamp string.
        """
        return value.isoformat()


def parse_sidecar_metadata(text: str) -> SidecarMetadata | None:
    """Parse external sidecar JSON into concrete metadata, or reject it.

    Returns:
        Validated metadata, or None when parsing fails.
    """
    try:
        return SidecarMetadata.model_validate_json(text)
    except ValidationError:
        return None
