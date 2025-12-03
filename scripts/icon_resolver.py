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
"""Icon resolution engine for tmux-nerd-icons.

This module provides the main icon resolution logic that matches process names,
window titles, session names, and SSH hosts against configuration to return
the appropriate nerd font icon.

Resolution priority:
    1. Host icon (if prefer-host-icon: true and SSH detected)
    2. Title patterns within app definitions (icons.*.title)
    3. Title icons for TUI apps (title_icons)
    4. Process name match (icons)
    5. Session keywords (sessions)
    6. Fallback icon

Example usage:
    from icon_resolver import resolve_icon

    result = resolve_icon(
        process="nvim",
        title="README.md",
        session="code",
    )
    print(result.icon)  #
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_parser import get_foreground_cmdline, parse_ssh_host
from yaml_parser import ParsedConfig, load_config

if TYPE_CHECKING:
    from yaml_parser import IconConfig

# Maximum regex pattern length for ReDoS protection
_MAX_PATTERN_LENGTH = 500


@dataclass
class IconResult:
    """Result of icon resolution.

    Attributes:
        icon: The resolved nerd font icon character.
        ring_color: Optional color for the tab ring/indicator.
        icon_color: Optional color for the icon itself.
        alert_color: Optional color for alert/bell state.
        source: Debug info indicating which resolution method matched.
            One of: host, title_pattern, title_icon, process, session, fallback.
    """

    icon: str
    ring_color: str | None = None
    icon_color: str | None = None
    alert_color: str | None = None
    source: str = "fallback"


# Configuration cache for hot reload
_config_cache: ParsedConfig | None = None
_config_mtime: float = 0.0
_config_path_cache: str = ""


def get_config(config_path: str) -> ParsedConfig:
    """Get configuration with caching and hot reload support.

    The configuration is cached and only reloaded when the file's mtime
    changes, enabling hot reload without restarting tmux.

    Args:
        config_path: Path to config file (supports ~ expansion).

    Returns:
        Parsed configuration object.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is invalid.
    """
    global _config_cache, _config_mtime, _config_path_cache

    path = os.path.expanduser(config_path)

    # Check file modification time
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        current_mtime = 0.0

    # Reload if cache is empty, path changed, or file was modified
    cache_invalid = (
        _config_cache is None or path != _config_path_cache or current_mtime > _config_mtime
    )

    if cache_invalid:
        _config_cache = load_config(path)
        _config_mtime = current_mtime
        _config_path_cache = path

    # At this point _config_cache is guaranteed to be set (either from cache or fresh load)
    assert _config_cache is not None
    return _config_cache


def _match_host(
    host: str,
    hosts: dict[str, str | dict[str, Any]],
    cfg: IconConfig,
) -> IconResult | None:
    """Match hostname against hosts configuration.

    Supports both exact matches and glob patterns (via fnmatch).
    All comparisons are case-insensitive.

    Args:
        host: Hostname to match (lowercase).
        hosts: Host configuration dictionary.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult if matched, None otherwise.
    """
    host_lower = host.lower()

    for pattern, value in hosts.items():
        pattern_lower = pattern.lower()

        # Check exact match first (fast path)
        if pattern_lower == host_lower:
            return _extract_host_result(value, cfg)

        # Check glob pattern (supports *, ?, [seq], [!seq])
        if fnmatch(host_lower, pattern_lower):
            return _extract_host_result(value, cfg)

    return None


def _extract_host_result(
    value: str | dict[str, Any],
    cfg: IconConfig,
) -> IconResult:
    """Extract IconResult from a host configuration value.

    Args:
        value: Either a simple icon string or a dict with icon and colors.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult with host source.
    """
    if isinstance(value, str):
        return IconResult(icon=value, source="host")

    return IconResult(
        icon=value.get("icon", cfg.fallback_icon),
        ring_color=value.get("ring-color") or value.get("index-color"),
        icon_color=value.get("icon-color"),
        alert_color=value.get("alert-color"),
        source="host",
    )


def _match_title_patterns(
    title: str,
    icons: dict[str, str | dict[str, Any]],
    cfg: IconConfig,
) -> IconResult | None:
    """Match window title against regex patterns in app definitions.

    This checks the 'title' sub-dictionary within each app's configuration
    for regex patterns that match the window title.

    Args:
        title: Window title to match.
        icons: Icons configuration dictionary.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult if matched, None otherwise.
    """
    if not title:
        return None

    for _app, value in icons.items():
        if not isinstance(value, dict):
            continue

        title_patterns = value.get("title")
        if not title_patterns or not isinstance(title_patterns, dict):
            continue

        for pattern, icon in title_patterns.items():
            # Security: limit pattern length for ReDoS protection
            if len(pattern) > _MAX_PATTERN_LENGTH:
                continue

            try:
                if re.search(pattern, title, re.IGNORECASE):
                    return IconResult(
                        icon=str(icon),
                        icon_color=value.get("icon-color"),
                        source="title_pattern",
                    )
            except re.error:
                # Invalid regex pattern, skip it
                continue

    return None


def _match_title_icons(
    title: str,
    title_icons: dict[str, str],
    cfg: IconConfig,
) -> IconResult | None:
    """Match window title against title_icons for TUI applications.

    Uses tokenized matching: the title is split into tokens and each
    token is checked against the title_icons keys. Also checks for
    substring matches.

    Args:
        title: Window title to match.
        title_icons: Title icons configuration dictionary.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult if matched, None otherwise.
    """
    if not title or not title_icons:
        return None

    title_lower = title.lower()

    # Tokenize title (split on non-alphanumeric characters, preserving ._+-)
    tokens = re.split(r"[^A-Za-z0-9._+-]+", title_lower)
    tokens = [t for t in tokens if t]

    # Check each token against title_icons (fast lookup)
    for token in tokens:
        if token in title_icons:
            return IconResult(icon=title_icons[token], source="title_icon")

    # Check if any title_icon key is a substring of the title
    for keyword, icon in title_icons.items():
        if keyword.lower() in title_lower:
            return IconResult(icon=icon, source="title_icon")

    return None


def _match_process(
    process: str,
    icons: dict[str, str | dict[str, Any]],
    cfg: IconConfig,
) -> IconResult | None:
    """Match process name against icons configuration.

    All comparisons are case-insensitive.

    Args:
        process: Process name to match.
        icons: Icons configuration dictionary.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult if matched, None otherwise.
    """
    if not process:
        return None

    process_lower = process.lower()

    # Direct lookup (case-insensitive by using lowercase icons keys)
    # Note: yaml_parser preserves case, so we need to search
    for key, value in icons.items():
        if key.lower() != process_lower:
            continue

        if isinstance(value, str):
            return IconResult(icon=value, source="process")

        return IconResult(
            icon=value.get("icon", cfg.fallback_icon),
            icon_color=value.get("icon-color"),
            source="process",
        )

    return None


def _match_session(
    session: str,
    sessions: dict[str, str],
    cfg: IconConfig,
) -> IconResult | None:
    """Match session name against session keywords.

    Uses tokenized matching: the session name is split into tokens
    and each token is checked against the sessions keys.

    Args:
        session: Tmux session name to match.
        sessions: Sessions configuration dictionary.
        cfg: Global icon configuration for defaults.

    Returns:
        IconResult if matched, None otherwise.
    """
    if not session or not sessions:
        return None

    session_lower = session.lower()

    # Tokenize session name (split on non-alphanumeric characters)
    tokens = re.split(r"[^A-Za-z0-9]+", session_lower)
    tokens = [t for t in tokens if t]

    # Check each token against sessions
    for token in tokens:
        if token in sessions:
            return IconResult(icon=sessions[token], source="session")

        # Also check lowercase keys for case-insensitive match
        for key, icon in sessions.items():
            if key.lower() == token:
                return IconResult(icon=icon, source="session")

    return None


def resolve_icon(
    process: str,
    title: str = "",
    session: str = "",
    cmdline: str | None = None,
    pane_pid: int | None = None,
    config_path: str = "~/.config/nerd-icons/config.yml",
) -> IconResult:
    """Resolve the appropriate icon for a tmux window/pane context.

    This is the main entry point for icon resolution. It applies the
    priority-based matching algorithm:

        1. Host icon (if prefer-host-icon and SSH detected)
        2. Title patterns within app definitions
        3. Title icons for TUI apps
        4. Process name match
        5. Session keywords
        6. Fallback icon

    Args:
        process: Foreground process name (e.g., "nvim", "zsh").
        title: Window/pane title.
        session: Tmux session name.
        cmdline: Full command line for SSH detection. If not provided
            and pane_pid is given, cmdline is retrieved from /proc.
        pane_pid: Pane PID for automatic cmdline retrieval.
        config_path: Path to configuration file.

    Returns:
        IconResult with the resolved icon and optional color metadata.
    """
    config = get_config(config_path)
    cfg = config.config

    # Get cmdline from PID if not provided directly
    effective_cmdline = cmdline
    if effective_cmdline is None and pane_pid is not None:
        cmdline_parts = get_foreground_cmdline(pane_pid)
        effective_cmdline = " ".join(cmdline_parts) if cmdline_parts else None

    # Detect SSH host from command line
    ssh_host: str | None = None
    if effective_cmdline:
        ssh_host = parse_ssh_host(effective_cmdline)

    # Priority 1: Host icon (if prefer-host-icon is enabled and SSH detected)
    if cfg.prefer_host_icon and ssh_host:
        result = _match_host(ssh_host, config.hosts, cfg)
        if result:
            return result

    # Priority 2: Title patterns within app definitions
    result = _match_title_patterns(title, config.icons, cfg)
    if result:
        return result

    # Priority 3: Title icons for TUI apps
    result = _match_title_icons(title, config.title_icons, cfg)
    if result:
        return result

    # Priority 4: Process name match
    result = _match_process(process, config.icons, cfg)
    if result:
        return result

    # Priority 5: Session keywords
    result = _match_session(session, config.sessions, cfg)
    if result:
        return result

    # Priority 6: Fallback icon
    return IconResult(icon=cfg.fallback_icon, source="fallback")


def main() -> int:
    """CLI entry point for icon resolution.

    Supports two output modes:
        --simple: Output just the icon character
        default: Output JSON with icon and metadata

    Returns:
        Exit code (0 for success, 1 for error).

    Examples:
        # Simple mode - just output icon
        python3 icon_resolver.py --simple --process nvim --title "README.md"

        # JSON mode - full result with colors
        python3 icon_resolver.py --process nvim --title "README.md" --session "code"

        # With SSH detection
        python3 icon_resolver.py --process ssh --cmdline "ssh user@malphas.local"
    """
    parser = argparse.ArgumentParser(
        description="Resolve nerd font icon for tmux window",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --simple --process nvim
  %(prog)s --simple --process zsh --session code
  %(prog)s --process ssh --cmdline "ssh user@example.com"
  %(prog)s --process zsh --pane-pid 12345
        """,
    )
    parser.add_argument(
        "--process",
        "-p",
        default="",
        help="Foreground process name",
    )
    parser.add_argument(
        "--title",
        "-t",
        default="",
        help="Window/pane title",
    )
    parser.add_argument(
        "--session",
        "-s",
        default="",
        help="Tmux session name",
    )
    parser.add_argument(
        "--cmdline",
        "-c",
        help="Full command line (for SSH detection)",
    )
    parser.add_argument(
        "--pane-pid",
        type=int,
        help="Pane PID for automatic cmdline retrieval",
    )
    parser.add_argument(
        "--config",
        default="~/.config/nerd-icons/config.yml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Output just the icon character (no JSON)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information on errors",
    )

    args = parser.parse_args()

    try:
        result = resolve_icon(
            process=args.process,
            title=args.title,
            session=args.session,
            cmdline=args.cmdline,
            pane_pid=args.pane_pid,
            config_path=args.config,
        )

        if args.simple:
            print(result.icon)
        else:
            print(json.dumps(asdict(result), ensure_ascii=False))

        return 0

    except FileNotFoundError as e:
        if args.debug:
            raise
        print(f"Error: Config file not found: {e}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as e:
        if args.debug:
            raise
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
