"""Zero-dependency YAML parser for nerd-icons configuration.

Supports indentation-based nesting, inline comments, quoted strings,
boolean parsing, and pre-lowercased lookup dicts for O(1) matching.

Security: 1MB max file size.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

# Security limits
MAX_CONFIG_SIZE = 1024 * 1024  # 1MB


@dataclass
class IconConfig:
    """Global configuration settings from the config: block."""

    fallback_icon: str = "?"
    show_name: bool = False
    use_process_name: bool = False
    prefer_host_icon: bool = False
    icon_position: str = "left"
    activity_pulse: bool = False
    pulse_interval_ms: int = 0
    pulse_duration_ms: int = 0
    index_color_active: str = ""
    index_color_inactive: str = ""
    alert_color: str = ""
    use_title_as_hostname: bool = False
    host_colors_only: bool = False
    prefer_session_icon: bool = True
    multi_pane_icon: str = ""
    layout_glyphs: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedConfig:
    """Complete parsed configuration from all YAML sections."""

    config: IconConfig
    icons: dict[str, str | dict[str, Any]]
    title_icons: dict[str, str]
    sessions: dict[str, str]
    hosts: dict[str, str | dict[str, Any]]

    # Pre-lowercased lookup dicts (computed once at load time)
    icons_lower: dict[str, str | dict[str, Any]] = field(default_factory=dict, repr=False)
    title_icons_lower: dict[str, str] = field(default_factory=dict, repr=False)
    sessions_lower: dict[str, str] = field(default_factory=dict, repr=False)
    hosts_lower: dict[str, str | dict[str, Any]] = field(default_factory=dict, repr=False)


class YamlParseError(ValueError):
    """Raised when YAML parsing fails."""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        if line_number is not None:
            message = f"Line {line_number}: {message}"
        super().__init__(message)


def _strip_yaml_value(val: str) -> str:
    """Strip inline comments and surrounding quotes from a YAML value."""
    val = val.strip()

    if val and val[0] in ('"', "'"):
        quote = val[0]
        end = val.find(quote, 1)
        if end > 0:
            return val[1:end]

    # Unquoted value: strip inline comments (space + #)
    if " #" in val:
        val = val.split(" #", 1)[0].strip()

    return val


def _normalize_yaml_key(raw: str, *, lowercase: bool = True) -> str:
    """Normalize a YAML key by stripping whitespace and quotes."""
    key = raw.strip()
    if len(key) >= 2 and key[0] in ('"', "'") and key[-1] == key[0]:
        key = key[1:-1]
    return key.lower() if lowercase else key


def _get_indent_level(line: str) -> int:
    """Get indentation level (number of leading spaces)."""
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    if indent > 0 and "\t" in line[:indent]:
        raise YamlParseError("Tabs are not allowed for indentation, use spaces")
    return indent


def _parse_bool(val: str) -> bool:
    """Parse a YAML boolean value."""
    v = val.lower().strip()
    return v in ("true", "yes", "1", "on")


def _is_inline_yaml_value(rest: str) -> bool:
    """Check if YAML value is inline (not a block indicator)."""
    if not rest:
        return False
    if rest[0] in ("|", ">", "{", "["):
        return False
    return not (rest[0] == "#" and (len(rest) == 1 or rest[1] == " "))


def _iter_yaml_block(
    lines: list[str],
    block_label: str,
) -> Iterator[tuple[str, str | None, int, int]]:
    """Iterate over items in a YAML block.

    Yields (key, inline_value_or_None, line_index, indent_level).
    """
    in_block = False
    block_indent: int | None = None
    target_label = f"{block_label}:"

    for idx, raw in enumerate(lines):
        stripped = raw.strip()

        if not in_block:
            if stripped == target_label or stripped.startswith(f"{target_label} "):
                in_block = True
            continue

        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue

        current_indent = _get_indent_level(raw)

        if block_indent is None:
            block_indent = current_indent

        if current_indent < block_indent:
            break

        if current_indent != block_indent:
            continue

        if ":" not in stripped:
            continue

        key_part, val_part = stripped.split(":", 1)
        key = _normalize_yaml_key(key_part, lowercase=False)
        rest = val_part.strip()

        if not key:
            continue

        if _is_inline_yaml_value(rest):
            inline_val = _strip_yaml_value(rest)
            yield (key, inline_val, idx, current_indent)
        else:
            yield (key, None, idx, current_indent)


def _parse_nested_block(
    lines: list[str],
    start_idx: int,
    base_indent: int,
) -> tuple[dict[str, Any], int]:
    """Parse a nested YAML block into a dictionary."""
    result: dict[str, Any] = {}
    idx = start_idx
    block_indent: int | None = None

    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()

        if not stripped or stripped.startswith("#"):
            idx += 1
            continue

        current_indent = _get_indent_level(raw)

        if current_indent <= base_indent:
            break

        if block_indent is None:
            block_indent = current_indent

        if current_indent > block_indent:
            idx += 1
            continue

        if ":" not in stripped:
            idx += 1
            continue

        key_part, val_part = stripped.split(":", 1)
        key = _normalize_yaml_key(key_part, lowercase=False)
        rest = val_part.strip()

        if not key:
            idx += 1
            continue

        if _is_inline_yaml_value(rest):
            result[key] = _strip_yaml_value(rest)
            idx += 1
        else:
            nested, idx = _parse_nested_block(lines, idx + 1, current_indent)
            if nested:
                result[key] = nested

    return result, idx


def _parse_config_section(lines: list[str]) -> IconConfig:
    """Parse the config: section into an IconConfig."""
    config = IconConfig()

    for key, value, _line_idx, _ in _iter_yaml_block(lines, "config"):
        if value is None:
            continue

        norm_key = key.lower().replace("-", "_")

        if norm_key == "fallback_icon" and value:
            config.fallback_icon = value
        elif norm_key == "show_name":
            config.show_name = _parse_bool(value)
        elif norm_key == "use_process_name":
            config.use_process_name = _parse_bool(value)
        elif norm_key == "prefer_host_icon":
            config.prefer_host_icon = _parse_bool(value)
        elif norm_key == "icon_position" and value:
            config.icon_position = value
        elif norm_key == "activity_pulse":
            config.activity_pulse = _parse_bool(value)
        elif norm_key == "pulse_interval_ms":
            try:
                config.pulse_interval_ms = int(value)
            except ValueError:
                pass
        elif norm_key == "pulse_duration_ms":
            try:
                config.pulse_duration_ms = int(value)
            except ValueError:
                pass
        elif norm_key == "index_color_active" and value:
            config.index_color_active = value
        elif norm_key == "index_color_inactive" and value:
            config.index_color_inactive = value
        elif norm_key == "alert_color" and value:
            config.alert_color = value
        elif norm_key == "use_title_as_hostname":
            config.use_title_as_hostname = _parse_bool(value)
        elif norm_key == "host_colors_only":
            config.host_colors_only = _parse_bool(value)
        elif norm_key == "prefer_session_icon":
            config.prefer_session_icon = _parse_bool(value)
        elif norm_key == "multi_pane_icon" and value:
            config.multi_pane_icon = value

    return config


def _parse_nested_section(lines: list[str], section: str) -> dict[str, str | dict[str, Any]]:
    """Parse a section with possible nested blocks (icons, hosts)."""
    result: dict[str, str | dict[str, Any]] = {}

    for key, value, line_idx, indent in _iter_yaml_block(lines, section):
        if value is not None:
            result[key] = value
        else:
            nested, _ = _parse_nested_block(lines, line_idx + 1, indent)
            if nested:
                result[key] = nested

    return result


def _parse_simple_section(lines: list[str], section: str) -> dict[str, str]:
    """Parse a simple key-value section (title_icons, sessions)."""
    result: dict[str, str] = {}

    for key, value, _line_idx, _indent in _iter_yaml_block(lines, section):
        if value is not None:
            result[key] = value

    return result


def _parse_layout_glyphs(lines: list[str]) -> dict[str, str]:
    """Parse layout-glyphs section (also accepts deprecated layout-glyps)."""
    result: dict[str, str] = {}

    for section in ("layout-glyps", "layout-glyphs"):
        for key, value, _line_idx, _indent in _iter_yaml_block(lines, section):
            if value is not None:
                result[key] = value

    return result


def load_config(path: str) -> ParsedConfig:
    """Load and parse the nerd-icons configuration file.

    Args:
        path: Path to config file (supports ~ expansion).

    Returns:
        ParsedConfig with all sections parsed.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is too large.
    """
    path = os.path.expanduser(path)

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read(MAX_CONFIG_SIZE + 1)
    except OSError as e:
        raise FileNotFoundError(f"Cannot access config file: {path}") from e

    if len(content) > MAX_CONFIG_SIZE:
        raise ValueError(f"Config file too large (max {MAX_CONFIG_SIZE} bytes)")

    return load_config_from_string(content)


def load_config_from_string(content: str) -> ParsedConfig:
    """Parse configuration from a string.

    Args:
        content: YAML content as string.

    Returns:
        ParsedConfig with all sections parsed.
    """
    lines = content.splitlines()

    config = _parse_config_section(lines)
    icons = _parse_nested_section(lines, "icons")
    title_icons = _parse_simple_section(lines, "title_icons")
    sessions = _parse_simple_section(lines, "sessions")
    hosts = _parse_nested_section(lines, "hosts")
    layout_glyphs = _parse_layout_glyphs(lines)

    config.layout_glyphs = layout_glyphs

    return ParsedConfig(
        config=config,
        icons=icons,
        title_icons=title_icons,
        sessions=sessions,
        hosts=hosts,
        icons_lower={k.lower(): v for k, v in icons.items()},
        title_icons_lower={k.lower(): v for k, v in title_icons.items()},
        sessions_lower={k.lower(): v for k, v in sessions.items()},
        hosts_lower={k.lower(): v for k, v in hosts.items()},
    )
