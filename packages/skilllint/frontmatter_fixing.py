"""Pure frontmatter fix planning.

This module computes schema-aware frontmatter rewrites without performing file
I/O, emitting diagnostics, selecting validators, or depending on rule/CLI
orchestration. FrontmatterValidator remains responsible for applying a plan
to disk and surfacing post-fix informational diagnostics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from skilllint.frontmatter_core import extract_frontmatter, fix_skill_name_field, get_frontmatter_model
from skilllint.frontmatter_yaml import (
    _dump_tool_list_fixes,
    _dump_yaml,
    _is_losslessly_scalar_tool_list,
    _replace_list_valued_tool_fields,
    safe_load_yaml_with_colon_fix,
)

if TYPE_CHECKING:
    from skilllint.models import YamlValue


@dataclass(frozen=True)
class FrontmatterFixPlan:
    """Result of planning frontmatter content repairs."""

    fixed_content: str
    fixes: tuple[str, ...]
    colon_fields: tuple[str, ...]


def _normalize_tool_fields_and_detect_changes(
    normalized_dict: dict[str, YamlValue],
    original_data: dict[str, YamlValue],
    frontmatter_text: str,
    *,
    colon_fixes: list[str],
    file_type: str,
    file_path: Path | None,
) -> tuple[dict[str, YamlValue], list[str]]:
    """Normalize schema-backed values and collect fix descriptions."""
    fixes = list(colon_fixes)
    if file_type == "skill" and file_path is not None:
        normalized_dict = fix_skill_name_field(normalized_dict, file_path, fixes)

    # Preserve authored skills scalar/list/null shape. It is not a declared
    # SKILL.md field, and AgentFrontmatter exposes a separate normalized view.
    if "skills" in original_data:
        normalized_dict["skills"] = original_data["skills"]

    tool_fields = {"tools", "disallowedTools", "allowed-tools"}
    for field_name in tool_fields:
        original_value = original_data.get(field_name)
        if isinstance(original_value, list) and _is_losslessly_scalar_tool_list(original_value):
            normalized_dict[field_name] = ", ".join(str(item) for item in original_value if item is not None)
            fixes.append(f"Converted {field_name} from YAML array to comma-separated string")

    for key, value in normalized_dict.items():
        if key in tool_fields:
            continue
        original_value = original_data.get(key)
        if original_value is not None and original_value != value:
            if isinstance(original_value, list) and isinstance(value, str):
                fixes.append(f"Converted {key} from YAML array to comma-separated string")
            elif isinstance(original_value, str) and "\n" in original_value and "\n" not in str(value):
                fixes.append(f"Normalized {key} to single line")

    if re.search(r":\s*[|>][-+]?", frontmatter_text):
        fixes.append("Removed YAML multiline indicators")

    return normalized_dict, fixes


def _compute_normalized_fixes(
    content: str,
    original_data: dict[str, YamlValue],
    frontmatter_text: str,
    body: str,
    *,
    file_type: str,
    file_path: Path | None,
    colon_fixes: list[str],
) -> tuple[str, list[str]] | None:
    """Compute normalized frontmatter content and fix descriptions."""
    model_class = get_frontmatter_model(file_type)
    if model_class is None:
        return None

    try:
        validated = model_class.model_validate(original_data)
        normalized_dict = cast(
            "dict[str, YamlValue]",
            validated.model_dump(by_alias=True, exclude_none=True, mode="python"),
        )
    except ValidationError:
        return (f"---\n{frontmatter_text}\n---\n{body}", colon_fixes) if colon_fixes else None

    normalized_dict, fixes = _normalize_tool_fields_and_detect_changes(
        normalized_dict,
        original_data,
        frontmatter_text,
        colon_fixes=colon_fixes,
        file_type=file_type,
        file_path=file_path,
    )

    for field_name in ("tools", "disallowedTools", "allowed-tools"):
        original_value = original_data.get(field_name)
        if isinstance(original_value, list) and not _is_losslessly_scalar_tool_list(original_value):
            normalized_dict[field_name] = original_value

    if not fixes:
        return None

    tool_list_fixes = {
        f"Converted {field_name} from YAML array to comma-separated string"
        for field_name in ("tools", "disallowedTools", "allowed-tools")
        if isinstance(original_data.get(field_name), list)
        and _is_losslessly_scalar_tool_list(original_data[field_name])
    }
    tool_values = {
        field_name: value
        for field_name, value in normalized_dict.items()
        if field_name in {"tools", "disallowedTools", "allowed-tools"}
        and isinstance(original_data.get(field_name), list)
        and _is_losslessly_scalar_tool_list(original_data[field_name])
        and isinstance(value, str)
    }

    if set(fixes) == tool_list_fixes:
        rewritten_frontmatter = _replace_list_valued_tool_fields(frontmatter_text, original_data)
        if rewritten_frontmatter is not None:
            return content.replace(frontmatter_text, rewritten_frontmatter, 1), fixes

    if len(tool_values) == len(fixes):
        yaml = _dump_tool_list_fixes(frontmatter_text, tool_values)
        if yaml is not None:
            return f"---\n{yaml}---\n{body}", fixes

    return f"---\n{_dump_yaml(normalized_dict)}---\n{body}", fixes


def plan_frontmatter_fixes(content: str, file_type: str, file_path: Path | None = None) -> FrontmatterFixPlan:
    """Compute frontmatter fixes without mutating the filesystem.

    Args:
        content: Full capability-file content.
        file_type: Frontmatter schema identifier such as skill or agent.
        file_path: Optional source path used for skill-name normalization.

    Returns:
        Immutable plan containing proposed content, descriptions, and fields
        recovered from unquoted-colon syntax.
    """
    frontmatter_text, _, _ = extract_frontmatter(content)
    end_match = re.search(r"\n---\s*\n", content[3:]) if frontmatter_text is not None else None
    if frontmatter_text is None or end_match is None:
        return FrontmatterFixPlan(content, (), ())

    body = content[end_match.end() + 3 :]
    parsed, _yaml_error, colon_fields, used_text = safe_load_yaml_with_colon_fix(frontmatter_text)
    colon_fixes = ["Quoted description value containing unquoted colon"] * len(colon_fields)

    if not isinstance(parsed, dict):
        return FrontmatterFixPlan(content, (), tuple(colon_fields))

    original_data = cast("dict[str, YamlValue]", parsed)
    computed = _compute_normalized_fixes(
        content,
        original_data,
        used_text,
        body,
        file_type=file_type,
        file_path=file_path,
        colon_fixes=colon_fixes,
    )
    if computed is None:
        return FrontmatterFixPlan(content, (), tuple(colon_fields))

    fixed_content, fixes = computed
    return FrontmatterFixPlan(fixed_content, tuple(fixes), tuple(colon_fields))


__all__ = ["FrontmatterFixPlan", "plan_frontmatter_fixes"]
