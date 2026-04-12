"""Icon resolution engine for nerd-icons.

Resolution priority (see RESOLUTION.md in nerd-icons core repo):
    1. Host icon (if prefer-host-icon and hostname provided)
    2. Compound match (icons entry + title sub-map regex)
    3. Icons with match: "any"/"title" matched via title token
    4. Title icons (title_icons token match)
    5. Process/class match (icons section, match: "process" or "any" via process)
    6. Session keyword match
    7. Fallback icon
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any

from .cache import get_config
from .parser import ParsedConfig

# Maximum regex pattern length for ReDoS protection
_MAX_PATTERN_LENGTH = 500

# Session token split: splits on all non-alphanumeric (including hyphens)
_SESSION_TOKEN_RE = re.compile(r"[^A-Za-z0-9]+")

# Glob metacharacters
_GLOB_CHARS = frozenset("*?[")


@dataclass
class IconResult:
    """Result of icon resolution."""

    icon: str
    icon_color: str | None = None
    ring_color: str | None = None
    alert_color: str | None = None
    source: str = "fallback"


def _value_to_icon_result(
    value: str | dict[str, Any],
    fallback_icon: str,
    source: str,
) -> IconResult:
    """Convert a config value (string or dict) to an IconResult."""
    if isinstance(value, str):
        return IconResult(icon=value, source=source)

    return IconResult(
        icon=value.get("icon", fallback_icon),
        ring_color=value.get("ring-color") or value.get("index-color"),
        icon_color=value.get("icon-color"),
        alert_color=value.get("alert-color"),
        source=source,
    )


def _match_host(
    hostname: str,
    hosts: dict[str, str | dict[str, Any]],
    hosts_lower: dict[str, str | dict[str, Any]],
    fallback_icon: str,
) -> IconResult | None:
    """Match hostname against hosts configuration.

    Uses lowercased hostname and hosts_lower for case-insensitive matching.
    Supports exact match and fnmatch glob patterns.
    """
    host_lower = hostname.lower()

    # O(1) exact match
    if host_lower in hosts_lower:
        return _value_to_icon_result(hosts_lower[host_lower], fallback_icon, "host")

    # Glob pattern fallback
    for pattern, value in hosts_lower.items():
        if _GLOB_CHARS.isdisjoint(pattern):
            continue
        if fnmatch(host_lower, pattern):
            return _value_to_icon_result(value, fallback_icon, "host")

    return None


def _key_matches_entry(
    key: str,
    entry: str | dict[str, Any],
    process: str,
    title: str,
) -> bool:
    """Check if an icons entry matches the given process/title per its match mode."""
    match_mode = "process"
    if isinstance(entry, dict):
        raw_match = entry.get("match", "process")
        # "both" is deprecated alias for "any"
        match_mode = "any" if raw_match == "both" else raw_match

    if match_mode == "process":
        return process == key
    elif match_mode == "title":
        return _key_in_title(key, title)
    elif match_mode == "any":
        return process == key or _key_in_title(key, title)
    return False


def _key_in_title(key: str, title: str) -> bool:
    """Check if key appears as a substring in the title (case-insensitive)."""
    if not title:
        return False
    return key.lower() in title.lower()


def _match_compound(
    process: str,
    title: str,
    icons: dict[str, str | dict[str, Any]],
    fallback_icon: str,
) -> IconResult | None:
    """Step 2: Compound match -- icons entry matches AND title sub-map regex matches."""
    if not title:
        return None

    for key, value in icons.items():
        if not isinstance(value, dict):
            continue

        title_patterns = value.get("title")
        if not title_patterns or not isinstance(title_patterns, dict):
            continue

        # Check if the entry matches the process/title
        if not _key_matches_entry(key, value, process, title):
            continue

        # Check title sub-map regex patterns
        for pattern, icon in title_patterns.items():
            if len(pattern) > _MAX_PATTERN_LENGTH:
                continue
            try:
                if re.search(pattern, title):
                    return IconResult(
                        icon=str(icon),
                        icon_color=value.get("icon-color"),
                        source="compound",
                    )
            except re.error:
                continue

    return None


def _match_title_via_icons(
    title: str,
    icons: dict[str, str | dict[str, Any]],
    fallback_icon: str,
) -> IconResult | None:
    """Step 3: Icons with match: 'any' or 'title' matched via title token."""
    if not title:
        return None

    title_lower = title.lower()

    for key, value in icons.items():
        if not isinstance(value, dict):
            continue

        raw_match = value.get("match", "process")
        match_mode = "any" if raw_match == "both" else raw_match

        if match_mode not in ("any", "title"):
            continue

        if key.lower() in title_lower:
            return _value_to_icon_result(value, fallback_icon, "process")

    return None


def _match_title_icons(
    title: str,
    title_icons: dict[str, str],
) -> IconResult | None:
    """Step 4: Token match against title_icons."""
    if not title or not title_icons:
        return None

    title_lower = title.lower()
    for key, icon in title_icons.items():
        if key.lower() in title_lower:
            return IconResult(icon=icon, source="title_icons")

    return None


def _match_process(
    process: str,
    title: str,
    icons: dict[str, str | dict[str, Any]],
    fallback_icon: str,
) -> IconResult | None:
    """Step 5: Simple process name match against icons."""
    if not process:
        return None

    value = icons.get(process)
    if value is None:
        return None

    # Check match mode
    if isinstance(value, dict):
        raw_match = value.get("match", "process")
        match_mode = "any" if raw_match == "both" else raw_match

        # match: "title" entries do NOT match via process name
        if match_mode == "title":
            return None

    return _value_to_icon_result(value, fallback_icon, "process")


def _match_session(
    session: str,
    sessions: dict[str, str],
) -> IconResult | None:
    """Step 6: Token match against sessions."""
    if not session or not sessions:
        return None

    # Full string match first
    if session in sessions:
        return IconResult(icon=sessions[session], source="session")

    # Token match (split on non-alphanumeric, including hyphens)
    tokens = [t for t in _SESSION_TOKEN_RE.split(session) if t]
    for token in tokens:
        if token in sessions:
            return IconResult(icon=sessions[token], source="session")

    return None


def _apply_host_colors(result: IconResult, host_result: IconResult | None) -> IconResult:
    """Apply host colors onto a resolved result (for host-colors-only mode)."""
    if host_result is None:
        return result
    if host_result.icon_color:
        result.icon_color = host_result.icon_color
    if host_result.ring_color:
        result.ring_color = host_result.ring_color
    if host_result.alert_color:
        result.alert_color = host_result.alert_color
    return result


def resolve_icon(
    process: str = "",
    title: str = "",
    session: str = "",
    hostname: str = "",
    config: ParsedConfig | None = None,
    config_path: str = "~/.config/nerd-icons/config.yml",
) -> IconResult:
    """Resolve the appropriate icon for a window context.

    Args:
        process: Process name or window class.
        title: Window title.
        session: Session or workspace name.
        hostname: SSH hostname (if already known).
        config: Pre-loaded config (skips file loading if provided).
        config_path: Path to configuration file.

    Returns:
        IconResult with the resolved icon and metadata.
    """
    if config is None:
        config = get_config(config_path)

    cfg = config.config
    fallback = cfg.fallback_icon

    # Step 1: Host icon/colors
    host_result = None
    if hostname:
        host_result = _match_host(hostname, config.hosts, config.hosts_lower, fallback)
        if host_result is not None and cfg.prefer_host_icon and not cfg.host_colors_only:
            return host_result

    # Step 2: Compound match (icons entry + title sub-map regex)
    result = _match_compound(process, title, config.icons, fallback)
    if result is not None:
        return _apply_host_colors(result, host_result)

    # Step 3: Icons with match: "any"/"title" matched via title token
    result = _match_title_via_icons(title, config.icons, fallback)
    if result is not None:
        return _apply_host_colors(result, host_result)

    # Step 4: Title icons
    result = _match_title_icons(title, config.title_icons)
    if result is not None:
        return _apply_host_colors(result, host_result)

    # Step 5: Simple process match
    result = _match_process(process, title, config.icons, fallback)
    if result is not None:
        return _apply_host_colors(result, host_result)

    # Step 6: Session keyword
    result = _match_session(session, config.sessions)
    if result is not None:
        return _apply_host_colors(result, host_result)

    # Step 7: Fallback
    return _apply_host_colors(IconResult(icon=fallback, source="fallback"), host_result)
