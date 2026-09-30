"""Dependency-light YAML parsing and round-trip repair for frontmatter.

This module owns syntax-level YAML helpers shared by validation, rules, and
boundary ingestion. It intentionally does not import the legacy
plugin_validator module or own schema/rule dispatch.
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.nodes import MappingNode, SequenceNode
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.tokens import CommentToken

from skilllint.frontmatter_core import extract_frontmatter

if TYPE_CHECKING:
    from skilllint.models import YamlValue

# Safe-mode parser for validation/ingestion.
_yaml_safe = YAML(typ="safe")

# Round-trip emitter for fixes that must preserve authored YAML structure.
_rt_yaml = YAML(typ="rt")
_rt_yaml.preserve_quotes = False
_rt_yaml.width = 10000  # prevent line wrapping


def _safe_load_yaml(text: str) -> YamlValue:
    """Parse a YAML string using ruamel.yaml safe loader.

    Args:
        text: YAML text to parse (frontmatter content, no --- delimiters).

    Returns:
        Parsed YAML data (dict, list, scalar, or None).
    """
    if not text or not text.strip():
        return {}
    return _yaml_safe.load(text)


def _dump_yaml(data: dict[str, YamlValue]) -> str:
    """Serialize a dict to YAML using the round-trip handler.

    Preserves key insertion order. Values containing ': ' are wrapped in
    double quotes so YAML parsers handle them correctly.

    Args:
        data: Dictionary to serialize.

    Returns:
        YAML string (may include trailing newline).
    """
    prepared: dict[str, YamlValue] = {}
    for key, value in data.items():
        if isinstance(value, str) and ": " in value:
            prepared[key] = DoubleQuotedScalarString(value)
        else:
            prepared[key] = value

    buf = StringIO()
    _rt_yaml.dump(prepared, buf)
    return buf.getvalue()


def _replace_list_valued_tool_fields(frontmatter_text: str, data: dict[str, YamlValue]) -> str | None:
    document = _rt_yaml.compose(frontmatter_text)
    if not isinstance(document, MappingNode) or document.flow_style:
        return None

    replacements: list[tuple[int, int, str]] = []
    replaced_fields: set[str] = set()
    for key_node, value_node in document.value:
        field_name = key_node.value
        value = data.get(field_name)
        if (
            field_name in {"tools", "disallowedTools", "allowed-tools"}
            and isinstance(value, list)
            and _is_losslessly_scalar_tool_list(value)
            and isinstance(value_node, SequenceNode)
        ):
            separator = frontmatter_text[key_node.end_mark.index : value_node.start_mark.index]
            if (
                value_node.start_mark.index < key_node.end_mark.index
                or "&" in frontmatter_text[key_node.end_mark.index : value_node.end_mark.index]
                or "#" in frontmatter_text[key_node.end_mark.index : value_node.end_mark.index]
                or not separator.startswith(":")
            ):
                return None
            scalar_buffer = StringIO()
            _rt_yaml.dump({"value": ", ".join(str(item) for item in value if item is not None)}, scalar_buffer)
            replacement_value = scalar_buffer.getvalue().removeprefix("value: ").rstrip()
            replacements.append((key_node.end_mark.index, value_node.end_mark.index, f": {replacement_value}"))
            replaced_fields.add(field_name)

    requested_fields = {
        field_name
        for field_name in ("tools", "disallowedTools", "allowed-tools")
        if _is_losslessly_scalar_tool_list(data.get(field_name))
    }
    if not replacements or replaced_fields != requested_fields:
        return None
    for start, end, replacement in reversed(replacements):
        frontmatter_text = f"{frontmatter_text[:start]}{replacement}{frontmatter_text[end:]}"
    return frontmatter_text


def _is_losslessly_scalar_tool_list(values: YamlValue) -> bool:
    if not isinstance(values, list):
        return False
    return all(
        str(value) and "," not in str(value) and not re.search(r"\s", str(value))
        for value in values
        if value is not None
    )


def _comment_lines(comment_data: object) -> list[str]:
    if isinstance(comment_data, CommentToken):
        return [line.removeprefix("#").removeprefix(" ") for line in comment_data.value.splitlines()]
    if isinstance(comment_data, list):
        return [line for item in comment_data for line in _comment_lines(item)]
    if isinstance(comment_data, tuple):
        return [line for item in comment_data for line in _comment_lines(item)]
    if isinstance(comment_data, dict):
        return [line for item in comment_data.values() for line in _comment_lines(item)]
    return []


def _dump_tool_list_fixes(frontmatter_text: str, tool_values: dict[str, str]) -> str | None:
    data = _rt_yaml.load(frontmatter_text)
    if not isinstance(data, CommentedMap):
        return None
    for field_name, value in tool_values.items():
        original_value = data.get(field_name)
        comment_lines = _comment_lines(data.ca.items.get(field_name))
        if isinstance(original_value, CommentedSeq) and original_value.anchor.value is not None:
            original_value.yaml_set_anchor(original_value.anchor.value, always_dump=True)
        if isinstance(original_value, CommentedSeq):
            comment_lines.extend(_comment_lines(original_value.ca.items))
        if comment_lines:
            data.yaml_set_comment_before_after_key(field_name, before="\n".join(comment_lines))
        data[field_name] = value
    buffer = StringIO()
    _rt_yaml.dump(data, buffer)
    return buffer.getvalue()


def _fix_unquoted_colons(frontmatter_text: str) -> tuple[str, list[str], list[str]]:
    """Quote description (and similar string) values that contain unquoted colons.

    Detects lines of the form ``key: value: more`` where the unquoted colon
    causes a YAML parse error and wraps the value in double-quotes.

    Args:
        frontmatter_text: Raw YAML frontmatter (without ``---`` delimiters).

    Returns:
        Tuple of (possibly-fixed frontmatter text, list of fix descriptions,
        list of field names that were fixed).  The field names list has one entry
        per fixed line and is used by callers to emit FM009 info issues.
    """
    fixes: list[str] = []
    fixed_fields: list[str] = []
    lines = frontmatter_text.splitlines(keepends=True)
    new_lines = []

    # Regex: key: value where value contains an unquoted colon
    # Only matches simple single-line scalar values, not block scalars or already-quoted values
    unquoted_colon_re = re.compile(r'^(\s*([\w-]+):\s+)([^\'"\[\{|>].+:.*)$')

    for line in lines:
        m = unquoted_colon_re.match(line.rstrip("\n"))
        if m:
            prefix = m.group(1)
            field_name = m.group(2)
            value = m.group(3)
            # Escape any existing double-quotes inside the value
            escaped = value.replace('"', '\\"')
            new_line = f'{prefix}"{escaped}"\n'
            fixes.append("Quoted description value containing unquoted colon")
            fixed_fields.append(field_name)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if fixes:
        return "".join(new_lines), fixes, fixed_fields
    return frontmatter_text, [], []


def safe_load_yaml_with_colon_fix(fm_text: str) -> tuple[dict | None, str | None, list[str], str]:
    """Parse YAML frontmatter, attempting unquoted-colon auto-fix on failure.

    Consolidates the try/except YAMLError -> _fix_unquoted_colons -> retry
    pattern used in multiple call sites.

    Args:
        fm_text: Raw YAML frontmatter text (without ``---`` delimiters).

    Returns:
        Tuple of (parsed_dict, yaml_error_msg, colon_fixed_fields, used_text).
        - parsed_dict: The parsed YAML dict, or None if parsing failed.
        - yaml_error_msg: Error message string if YAML parsing failed
          even after colon fix, or None on success.
        - colon_fixed_fields: List of field names where unquoted colons
          were detected and auto-fixed (empty if no fix was needed).
        - used_text: The frontmatter text that was successfully parsed
          (may be the colon-fixed version if auto-fix was applied).
    """
    try:
        data = _safe_load_yaml(fm_text)
    except YAMLError as exc:
        fixed_fm, colon_fixes, colon_fields = _fix_unquoted_colons(fm_text)
        if colon_fixes:
            try:
                data = _safe_load_yaml(fixed_fm)
            except YAMLError:
                pass
            else:
                parsed = dict(data) if isinstance(data, dict) else None
                return parsed, None, colon_fields, fixed_fm
        return None, str(exc), [], fm_text
    else:
        parsed = dict(data) if isinstance(data, dict) else None
        return parsed, None, [], fm_text


def parse_skill_md(path: Path) -> tuple[dict, list[str], str | None, list[str]]:
    """Parse a SKILL.md file into frontmatter data and body lines.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        Tuple of (frontmatter dict, body lines, YAML error message,
        colon-recovered field names). Body lines exclude the closing
        frontmatter delimiter. An unterminated opening delimiter has no
        recoverable body and returns an empty body.
    """
    content = path.read_text(encoding="utf-8")
    fm_text, _start, end_line = extract_frontmatter(content)
    if fm_text is None:
        if content.startswith("---"):
            return {}, [], None, []
        return {}, content.splitlines(), None, []

    parsed, yaml_err, colon_fields, _used_text = safe_load_yaml_with_colon_fix(fm_text)
    frontmatter_dict: dict = parsed if parsed is not None else {}
    body_lines = content.splitlines()[end_line + 1 :]
    return frontmatter_dict, body_lines, yaml_err, colon_fields


__all__ = ["parse_skill_md", "safe_load_yaml_with_colon_fix"]
