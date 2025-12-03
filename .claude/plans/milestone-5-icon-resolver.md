# Milestone 5: Icon Resolver

**Target File:** `/home/rain/projects/tmux-nerd-icons/scripts/icon_resolver.py`

**Dependencies:** Milestone 3 (yaml_parser.py), Milestone 4 (ssh_parser.py)

## Purpose

Main icon resolution engine that matches process names, window titles, session names,
and SSH hosts against the configuration to return the appropriate icon.

## Requirements

1. Python 3.10+
2. Import yaml_parser and ssh_parser modules
3. Implement priority-based icon matching
4. Support regex title patterns
5. Support glob patterns for host matching
6. Cache config with mtime checking for hot reload
7. Return icon with optional color metadata

## Icon Resolution Priority

1. **Host icon** (if `prefer-host-icon: true` and SSH detected)
2. **Title patterns** within app definitions (`icons.*.title`)
3. **Title icons** for TUI apps (`title_icons`)
4. **Process name** match (`icons`)
5. **Session keywords** (`sessions`)
6. **Fallback icon** (`config.fallback-icon`)

## Data Structures

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class IconResult:
    """Result of icon resolution."""
    icon: str
    ring_color: str | None = None
    icon_color: str | None = None
    alert_color: str | None = None
    source: str = "fallback"  # For debugging: host, title, process, session, fallback
```

## Core Algorithm

```python
import re
from fnmatch import fnmatch
from yaml_parser import load_config, ParsedConfig, IconConfig
from ssh_parser import parse_ssh_host

# Configuration cache
_config_cache: ParsedConfig | None = None
_config_mtime: float = 0.0


def get_config(config_path: str) -> ParsedConfig:
    """Get config with caching and hot reload."""
    global _config_cache, _config_mtime

    path = os.path.expanduser(config_path)
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        current_mtime = 0.0

    if _config_cache is None or current_mtime > _config_mtime:
        _config_cache = load_config(path)
        _config_mtime = current_mtime

    return _config_cache


def resolve_icon(
    process: str,
    title: str,
    session: str,
    cmdline: str | None = None,
    config_path: str = "~/.config/nerd-icons/config.yml",
) -> IconResult:
    """
    Resolve icon for given window context.

    Args:
        process: Foreground process name (e.g., "nvim", "zsh")
        title: Window/pane title
        session: Tmux session name
        cmdline: Full command line for SSH detection
        config_path: Path to config file

    Returns:
        IconResult with icon and optional colors
    """
    config = get_config(config_path)
    cfg = config.config

    # Detect SSH host
    ssh_host = None
    if cmdline:
        ssh_host = parse_ssh_host(cmdline)

    # Priority 1: Host icon
    if cfg.prefer_host_icon and ssh_host:
        result = _match_host(ssh_host, config.hosts, cfg)
        if result:
            return result

    # Priority 2: Title patterns within app definitions
    result = _match_title_patterns(title, config.icons, cfg)
    if result:
        return result

    # Priority 3: Title icons (TUI apps)
    result = _match_title_icons(title, config.title_icons, cfg)
    if result:
        return result

    # Priority 4: Process name
    result = _match_process(process, config.icons, cfg)
    if result:
        return result

    # Priority 5: Session keywords
    result = _match_session(session, config.sessions, cfg)
    if result:
        return result

    # Fallback
    return IconResult(icon=cfg.fallback_icon, source="fallback")


def _match_host(
    host: str,
    hosts: dict[str, str | dict[str, Any]],
    cfg: IconConfig,
) -> IconResult | None:
    """Match hostname against hosts config (supports glob patterns)."""
    host_lower = host.lower()

    for pattern, value in hosts.items():
        # Check exact match first
        if pattern.lower() == host_lower:
            return _extract_host_result(value, cfg)

        # Check glob pattern
        if fnmatch(host_lower, pattern.lower()):
            return _extract_host_result(value, cfg)

    return None


def _extract_host_result(
    value: str | dict[str, Any],
    cfg: IconConfig,
) -> IconResult:
    """Extract IconResult from host config value."""
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
    """Match title against regex patterns in icon definitions."""
    for app, value in icons.items():
        if not isinstance(value, dict):
            continue

        title_patterns = value.get("title")
        if not title_patterns or not isinstance(title_patterns, dict):
            continue

        for pattern, icon in title_patterns.items():
            # Security: limit pattern length
            if len(pattern) > 500:
                continue

            try:
                if re.search(pattern, title, re.IGNORECASE):
                    return IconResult(
                        icon=icon,
                        icon_color=value.get("icon-color"),
                        source="title_pattern",
                    )
            except re.error:
                continue  # Invalid regex, skip

    return None


def _match_title_icons(
    title: str,
    title_icons: dict[str, str],
    cfg: IconConfig,
) -> IconResult | None:
    """Match title against title_icons for TUI apps."""
    title_lower = title.lower()

    # Tokenize title
    tokens = re.split(r"[^A-Za-z0-9._+-]+", title_lower)
    tokens = [t for t in tokens if t]

    # Check each token
    for token in tokens:
        if token in title_icons:
            return IconResult(icon=title_icons[token], source="title_icon")

    # Check if any title_icon key is a substring
    for keyword, icon in title_icons.items():
        if keyword in title_lower:
            return IconResult(icon=icon, source="title_icon")

    return None


def _match_process(
    process: str,
    icons: dict[str, str | dict[str, Any]],
    cfg: IconConfig,
) -> IconResult | None:
    """Match process name against icons config."""
    process_lower = process.lower()

    if process_lower not in icons:
        return None

    value = icons[process_lower]

    if isinstance(value, str):
        return IconResult(icon=value, source="process")

    return IconResult(
        icon=value.get("icon", cfg.fallback_icon),
        icon_color=value.get("icon-color"),
        source="process",
    )


def _match_session(
    session: str,
    sessions: dict[str, str],
    cfg: IconConfig,
) -> IconResult | None:
    """Match session name against session keywords."""
    session_lower = session.lower()

    # Tokenize session name
    tokens = re.split(r"[^A-Za-z0-9]+", session_lower)
    tokens = [t for t in tokens if t]

    for token in tokens:
        if token in sessions:
            return IconResult(icon=sessions[token], source="session")

    return None
```

## CLI Interface

```bash
# Simple mode - just output icon
python3 scripts/icon_resolver.py --simple \
    --process nvim \
    --title "README.md" \
    --session "code"
# Output:

# JSON mode - full result with colors
python3 scripts/icon_resolver.py \
    --process nvim \
    --title "README.md" \
    --session "code"
# Output: {"icon": "", "ring_color": null, "icon_color": null, "source": "process"}

# With SSH detection
python3 scripts/icon_resolver.py \
    --process ssh \
    --cmdline "ssh user@malphas.local"
# Output: {"icon": "", "ring_color": "#04a5e5", ...}
```

## Full Implementation

```python
#!/usr/bin/env python3
"""
icon_resolver.py - Resolve nerd font icons for tmux windows.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.
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
from yaml_parser import ParsedConfig, load_config
from ssh_parser import parse_ssh_host, get_foreground_cmdline

if TYPE_CHECKING:
    from yaml_parser import IconConfig


@dataclass
class IconResult:
    """Result of icon resolution."""
    icon: str
    ring_color: str | None = None
    icon_color: str | None = None
    alert_color: str | None = None
    source: str = "fallback"


# Cache
_config_cache: ParsedConfig | None = None
_config_mtime: float = 0.0


def get_config(config_path: str) -> ParsedConfig:
    """Get config with caching."""
    global _config_cache, _config_mtime

    path = os.path.expanduser(config_path)
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        current_mtime = 0.0

    if _config_cache is None or current_mtime > _config_mtime:
        _config_cache = load_config(path)
        _config_mtime = current_mtime

    return _config_cache


def resolve_icon(
    process: str,
    title: str = "",
    session: str = "",
    cmdline: str | None = None,
    pane_pid: int | None = None,
    config_path: str = "~/.config/nerd-icons/config.yml",
) -> IconResult:
    """Resolve icon for given window context."""
    config = get_config(config_path)
    cfg = config.config

    # Get cmdline from PID if not provided
    if cmdline is None and pane_pid is not None:
        cmdline_list = get_foreground_cmdline(pane_pid)
        cmdline = " ".join(cmdline_list) if cmdline_list else None

    # Detect SSH
    ssh_host = parse_ssh_host(cmdline) if cmdline else None

    # Priority 1: Host
    if cfg.prefer_host_icon and ssh_host:
        result = _match_host(ssh_host, config.hosts, cfg)
        if result:
            return result

    # Priority 2: Title patterns
    result = _match_title_patterns(title, config.icons, cfg)
    if result:
        return result

    # Priority 3: Title icons
    result = _match_title_icons(title, config.title_icons, cfg)
    if result:
        return result

    # Priority 4: Process
    result = _match_process(process, config.icons, cfg)
    if result:
        return result

    # Priority 5: Session
    result = _match_session(session, config.sessions, cfg)
    if result:
        return result

    return IconResult(icon=cfg.fallback_icon)


# ... (helper functions as shown above) ...


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Resolve nerd font icon for tmux window"
    )
    parser.add_argument("--process", "-p", default="", help="Process name")
    parser.add_argument("--title", "-t", default="", help="Window title")
    parser.add_argument("--session", "-s", default="", help="Session name")
    parser.add_argument("--cmdline", "-c", help="Full command line")
    parser.add_argument("--pane-pid", type=int, help="Pane PID for cmdline")
    parser.add_argument("--config", default="~/.config/nerd-icons/config.yml")
    parser.add_argument("--simple", action="store_true", help="Output icon only")
    parser.add_argument("--debug", action="store_true", help="Debug output")

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
            print(json.dumps(asdict(result)))

        return 0

    except Exception as e:
        if args.debug:
            raise
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

## Testing

```python
def test_process_match():
    result = resolve_icon(process="nvim", title="", session="")
    assert result.icon == ""
    assert result.source == "process"

def test_title_pattern():
    result = resolve_icon(process="firefox", title="GitHub - repo")
    assert result.icon == ""
    assert result.source == "title_pattern"

def test_host_match():
    result = resolve_icon(
        process="ssh",
        cmdline="ssh user@malphas.local"
    )
    assert result.icon == ""
    assert result.source == "host"

def test_session_keyword():
    result = resolve_icon(process="zsh", session="my-code-project")
    assert result.icon == "󰨞"
    assert result.source == "session"
```

## Linting

```bash
ruff check scripts/icon_resolver.py
ruff format --check scripts/icon_resolver.py
mypy --strict scripts/icon_resolver.py
```

## Reference

Pattern follows `/home/rain/.config/kitty/tab_bar.py` lines 750-850.
