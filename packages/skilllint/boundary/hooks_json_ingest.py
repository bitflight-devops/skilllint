"""Ingest ``hooks.json`` at a typed boundary for the HK-series rules.

``hooks.json`` is untrusted external JSON, so it enters through this module
rather than through ``skilllint.rules.hk_series``. See ``docs/TYPING_POLICY.md``
sections 4-6: raw payloads are validated here with Pydantic (strict) and only
concrete types cross into the rules package.

Scope of validation is deliberately shallow. HK001 owns exactly four structural
failures -- unreadable file, unparseable JSON, absent top-level ``hooks`` key,
and a ``hooks`` value that is not an object -- and HK002/HK003 exist to *report*
on whatever is nested inside that object. Validating the nested hook groups here
would leave those rules nothing to describe, so the nested values are typed as
:data:`pydantic.JsonValue` and inspected downstream.

Failures are returned as a :class:`HooksJsonDefect` rather than raised, and
rather than as a ``ValidationIssue``: rule wording, severity and documentation
anchors belong to the rule that owns the code, not to the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgspec.json
from pydantic import JsonValue, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["HooksJsonDefect", "ingest_hooks_json"]

# A JSON object with unconstrained values. Used twice: once to prove the
# document root is an object, once to prove its "hooks" value is an object.
# strict=True so a producer that emits, say, a JSON string where an object is
# declared is rejected rather than coerced (TYPING_POLICY.md 8.2).
_JSON_OBJECT_ADAPTER: TypeAdapter[dict[str, JsonValue]] = TypeAdapter(dict[str, JsonValue])


@dataclass(frozen=True, slots=True)
class HooksJsonDefect:
    """A structural reason ``hooks.json`` yielded no usable hooks object.

    Attributes:
        field: JSON path (or pseudo-path such as ``(file)``) of the failure,
            suitable for a ``ValidationIssue.field``.
        message: Human-readable description of what is wrong.
        suggestion: Optional repair hint, or ``None`` when the message is
            self-explanatory.
    """

    field: str
    message: str
    suggestion: str | None = None


def _as_json_object(value: object) -> dict[str, JsonValue] | None:
    """Validate *value* as a JSON object, strictly.

    Args:
        value: A value produced by JSON decoding.

    Returns:
        The value as a concrete ``dict[str, JsonValue]``, or ``None`` when it is
        not a JSON object.
    """
    try:
        return _JSON_OBJECT_ADAPTER.validate_python(value, strict=True)
    except ValidationError:
        return None


def ingest_hooks_json(path: Path) -> dict[str, JsonValue] | HooksJsonDefect:
    """Read *path* and return its validated top-level ``hooks`` object.

    Args:
        path: Path to a ``hooks.json`` file.

    Returns:
        The ``hooks`` object as a concrete ``dict[str, JsonValue]``, or a
        :class:`HooksJsonDefect` describing why no such object could be produced.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return HooksJsonDefect(field="(file)", message=f"Could not read file: {e}")

    try:
        decoded = msgspec.json.decode(content)
    except msgspec.DecodeError as e:
        return HooksJsonDefect(
            field="(json)", message=f"Invalid JSON syntax: {e}", suggestion="Fix JSON syntax errors in hooks.json"
        )

    document = _as_json_object(decoded)
    if document is None or "hooks" not in document:
        return HooksJsonDefect(
            field="hooks",
            message="Missing required top-level 'hooks' key",
            suggestion='hooks.json must have structure: {"hooks": {...}}',
        )

    hooks = _as_json_object(document["hooks"])
    if hooks is None:
        return HooksJsonDefect(field="hooks", message="'hooks' value must be an object")

    return hooks
