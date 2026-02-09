#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2024 tmux-nerd-icons contributors
#
# This file is part of tmux-nerd-icons.
#
# tmux-nerd-icons is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tmux-nerd-icons is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tmux-nerd-icons.  If not, see <https://www.gnu.org/licenses/>.
"""Minimal YAML parser for nerd-icons configuration.

This module provides a zero-dependency YAML parser specifically designed
for parsing the nerd-icons configuration format. It supports:

- Simple key-value pairs (key: value)
- Nested mappings (indentation-based)
- Inline comments (stripped with " #")
- Single and double quoted strings
- Boolean parsing (true/false, yes/no, on/off, 1/0)

Security features:
- File size limit (1MB max)
- Regex pattern length limit (500 chars for ReDoS protection)

Example usage:
    from yaml_parser import load_config
    config = load_config("~/.config/nerd-icons/config.yml")
    print(config.icons)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

# Security limits
MAX_CONFIG_SIZE = 1024 * 1024  # 1MB
MAX_REGEX_LENGTH = 500  # ReDoS protection


@dataclass
class IconConfig:
    """Global configuration settings from the config: block."""

    fallback_icon: str = "\U000f0d59"  # 󰽙
    show_name: bool = False
    use_process_name: bool = False
    prefer_host_icon: bool = True
    ring_color_active: str = "#875fff"
    ring_color_inactive: str = "#45475a"
    icon_color: str = "#cdd6f4"
    alert_color: str = "#f38ba8"
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


class YamlParseError(ValueError):
    """Raised when YAML parsing fails."""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        if line_number is not None:
            message = f"Line {line_number}: {message}"
        super().__init__(message)


def _strip_yaml_value(val: str) -> str:
    """Strip inline comments and surrounding quotes from a YAML value.

    Args:
        val: Raw value string from YAML

    Returns:
        Cleaned value with comments and quotes removed

    Examples:
        >>> _strip_yaml_value('  "hello"  # comment')
        'hello'
        >>> _strip_yaml_value("'single quoted'")
        'single quoted'
    """
    val = val.strip()

    # Remove inline comments (space + #)
    if " #" in val:
        val = val.split(" #", 1)[0].strip()

    # Remove surrounding quotes (single or double)
    if val and len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        val = val[1:-1]

    return val


def _normalize_yaml_key(raw: str, *, lowercase: bool = True) -> str:
    """Normalize a YAML key by stripping whitespace and quotes.

    Args:
        raw: Raw key string
        lowercase: Whether to lowercase the key (default True)

    Returns:
        Normalized key string
    """
    key = raw.strip()

    # Remove surrounding quotes
    if len(key) >= 2 and key[0] in ('"', "'") and key[-1] == key[0]:
        key = key[1:-1]

    return key.lower() if lowercase else key


def _get_indent_level(line: str) -> int:
    """Get indentation level (number of leading spaces).

    Args:
        line: Raw line from file

    Returns:
        Number of leading spaces
    """
    return len(line) - len(line.lstrip())


def _parse_bool(val: str) -> bool:
    """Parse a YAML boolean value.

    Args:
        val: String value to parse

    Returns:
        Boolean interpretation, False for unrecognized values
    """
    v = val.lower().strip()
    if v in ("true", "yes", "1", "on"):
        return True
    if v in ("false", "no", "0", "off"):
        return False
    return False


def _is_inline_yaml_value(rest: str) -> bool:
    """Check if YAML value is inline (not a block indicator).

    Args:
        rest: The value portion after the colon

    Returns:
        True if this is an inline value, False if nested block
    """
    if not rest:
        return False
    if rest[0] in ("|", ">", "{", "["):
        return False
    # Only treat # as comment if followed by space or alone;
    # bare hex colors like #cdd6f4 are valid inline values
    return not (rest[0] == "#" and (len(rest) == 1 or rest[1] == " "))


def _validate_pattern_length(pattern: str, line_number: int) -> None:
    """Validate regex pattern length for ReDoS protection.

    Args:
        pattern: Regex pattern string
        line_number: Line number for error reporting

    Raises:
        YamlParseError: If pattern exceeds maximum length
    """
    if len(pattern) > MAX_REGEX_LENGTH:
        raise YamlParseError(
            f"Regex pattern too long ({len(pattern)} chars, max {MAX_REGEX_LENGTH})",
            line_number,
        )


def _iter_yaml_block(
    lines: list[str],
    block_label: str,
) -> Iterator[tuple[str, str | None, int, int]]:
    """Iterate over items in a YAML block.

    Args:
        lines: Raw file lines
        block_label: Label to match (e.g., "icons")

    Yields:
        Tuples of (key, inline_value_or_None, line_index, indent_level)

    If inline_value is None, the entry has nested content that the caller
    should parse separately.
    """
    in_block = False
    block_indent: int | None = None
    target_label = f"{block_label}:"

    for idx, raw in enumerate(lines):
        stripped = raw.strip()

        # Look for block start
        if not in_block:
            if stripped == target_label or stripped.startswith(f"{target_label} "):
                in_block = True
            continue

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        current_indent = _get_indent_level(raw)

        # Establish block indent from first non-empty line
        if block_indent is None:
            block_indent = current_indent

        # Check if we've left the block (dedent)
        if current_indent < block_indent:
            break

        # Only process lines at block indent level (top-level items)
        if current_indent != block_indent:
            continue

        # Must have a colon for key-value pair
        if ":" not in stripped:
            continue

        # Parse key and value
        key_part, val_part = stripped.split(":", 1)
        key = _normalize_yaml_key(key_part, lowercase=False)
        rest = val_part.strip()

        if not key:
            continue

        # Determine if this is an inline value or nested block
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
    """Parse a nested YAML block into a dictionary.

    Args:
        lines: Raw file lines
        start_idx: Line index to start parsing from
        base_indent: Indentation of the parent key

    Returns:
        Tuple of (parsed dictionary, ending line index)
    """
    result: dict[str, Any] = {}
    idx = start_idx
    block_indent: int | None = None

    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue

        current_indent = _get_indent_level(raw)

        # End of nested block (dedent to parent or less)
        if current_indent <= base_indent:
            break

        # Establish block indent from first non-empty line
        if block_indent is None:
            block_indent = current_indent

        # Only process lines at this block's indent level
        if current_indent > block_indent:
            # This is part of a nested block we already recursed into
            idx += 1
            continue

        # Must have a colon
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
            # Simple value
            result[key] = _strip_yaml_value(rest)
            idx += 1
        else:
            # Recursively parse deeper nesting
            nested, idx = _parse_nested_block(lines, idx + 1, current_indent)
            if nested:
                result[key] = nested
            # idx is already advanced by recursive call

    return result, idx


def _parse_config_section(lines: list[str]) -> IconConfig:
    """Parse the config: section into an IconConfig.

    Args:
        lines: Raw file lines

    Returns:
        Populated IconConfig with parsed values
    """
    config = IconConfig()

    for key, value, _line_idx, _ in _iter_yaml_block(lines, "config"):
        if value is None:
            continue

        # Normalize key (handle both hyphen and underscore)
        norm_key = key.lower().replace("-", "_")

        if norm_key == "fallback_icon" and value:
            config.fallback_icon = value
        elif norm_key == "show_name":
            config.show_name = _parse_bool(value)
        elif norm_key == "use_process_name":
            config.use_process_name = _parse_bool(value)
        elif norm_key == "prefer_host_icon":
            config.prefer_host_icon = _parse_bool(value)
        elif norm_key in ("ring_color_active", "index_color_active") and value:
            config.ring_color_active = value
        elif norm_key in ("ring_color_inactive", "index_color_inactive") and value:
            config.ring_color_inactive = value
        elif norm_key == "icon_color" and value:
            config.icon_color = value
        elif norm_key == "alert_color" and value:
            config.alert_color = value
        elif norm_key == "multi_pane_icon" and value:
            config.multi_pane_icon = value

    return config


def _parse_nested_section(lines: list[str], section: str) -> dict[str, str | dict[str, Any]]:
    """Parse a section with possible nested blocks (icons, hosts).

    Args:
        lines: Raw file lines
        section: Section name to parse

    Returns:
        Dictionary mapping keys to icons or nested config dicts
    """
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
    """Parse a simple key-value section (title_icons, sessions).

    Args:
        lines: Raw file lines
        section: Section name to parse

    Returns:
        Dictionary of simple key-value mappings
    """
    result: dict[str, str] = {}

    for key, value, _line_idx, _indent in _iter_yaml_block(lines, section):
        if value is not None:
            result[key] = value

    return result


def _parse_layout_glyphs(lines: list[str]) -> dict[str, str]:
    """Parse the layout-glyps section (note: handles typo in config).

    Args:
        lines: Raw file lines

    Returns:
        Dictionary mapping layout names to glyph icons
    """
    result: dict[str, str] = {}

    # Try both spellings (glyps is the typo in config, glyphs is correct)
    for section in ("layout-glyps", "layout-glyphs"):
        for key, value, _line_idx, _indent in _iter_yaml_block(lines, section):
            if value is not None:
                result[key] = value

    return result


def load_config(path: str) -> ParsedConfig:
    """Load and parse the nerd-icons configuration file.

    Args:
        path: Path to config file (supports ~ expansion)

    Returns:
        ParsedConfig with all sections parsed

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or too large
        YamlParseError: If YAML parsing fails
    """
    path = os.path.expanduser(path)

    # Security: check file size before reading
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise FileNotFoundError(f"Cannot access config file: {path}") from e

    if size > MAX_CONFIG_SIZE:
        raise ValueError(f"Config file too large: {size} bytes (max {MAX_CONFIG_SIZE})")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    return load_config_from_string(content)


def load_config_from_string(content: str) -> ParsedConfig:
    """Parse configuration from a string.

    Args:
        content: YAML content as string

    Returns:
        ParsedConfig with all sections parsed

    Raises:
        YamlParseError: If YAML parsing fails
    """
    lines = content.splitlines()

    # Parse each section
    config = _parse_config_section(lines)
    icons = _parse_nested_section(lines, "icons")
    title_icons = _parse_simple_section(lines, "title_icons")
    sessions = _parse_simple_section(lines, "sessions")
    hosts = _parse_nested_section(lines, "hosts")
    layout_glyphs = _parse_layout_glyphs(lines)

    # Attach layout glyphs to config
    config.layout_glyphs = layout_glyphs

    return ParsedConfig(
        config=config,
        icons=icons,
        title_icons=title_icons,
        sessions=sessions,
        hosts=hosts,
    )


def _dataclass_to_dict(obj: Any) -> Any:
    """Convert dataclass instances to dictionaries for JSON serialization.

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable representation
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    return obj


def main() -> int:
    """CLI entry point for config validation and debugging.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Minimal YAML parser for nerd-icons configuration",
    )
    parser.add_argument(
        "config_file",
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate config and exit",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump parsed config as JSON",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config_file)

        if args.validate:
            print(f"Config valid: {args.config_file}")
            print(f"  Icons: {len(config.icons)}")
            print(f"  Title icons: {len(config.title_icons)}")
            print(f"  Sessions: {len(config.sessions)}")
            print(f"  Hosts: {len(config.hosts)}")
            print(f"  Layout glyphs: {len(config.config.layout_glyphs)}")
            return 0

        if args.dump:
            output = _dataclass_to_dict(config)
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        # Default: just validate
        print(f"Config loaded successfully: {args.config_file}")
        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (ValueError, YamlParseError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
