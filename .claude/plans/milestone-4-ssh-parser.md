# Milestone 4: SSH Parser

**Target File:** `/home/rain/projects/tmux-nerd-icons/scripts/ssh_parser.py`

**Dependencies:** None (can be developed in parallel)

## Purpose

Parse SSH and mosh command lines to extract the target hostname for host-specific
icon matching.

## Requirements

1. Python 3.10+
2. No external dependencies
3. Handle ssh, slogin, mosh, mosh-client commands
4. Skip SSH options that consume arguments (-i, -p, -l, etc.)
5. Strip user@ prefix
6. Strip IPv6 brackets
7. Strip port suffix
8. Return normalized lowercase hostname

## SSH Options That Take Arguments

```python
# Options that consume the next argument
_SSH_OPTIONS_WITH_ARG = frozenset((
    "-b",  # bind address
    "-c",  # cipher spec
    "-D",  # dynamic port forward
    "-E",  # log file
    "-F",  # config file
    "-I",  # PKCS#11 shared library
    "-i",  # identity file
    "-J",  # jump host
    "-L",  # local port forward
    "-l",  # login name
    "-m",  # MAC spec
    "-O",  # control command
    "-o",  # option
    "-p",  # port
    "-Q",  # query
    "-R",  # remote port forward
    "-S",  # control socket
    "-W",  # stdio forward
    "-w",  # tunnel device
    "-B",  # bind interface
))
```

## Core Algorithm

```python
def parse_ssh_host(cmdline: str | list[str]) -> str | None:
    """
    Parse SSH/mosh command line to extract target hostname.

    Args:
        cmdline: Command line as string or list of arguments

    Returns:
        Normalized hostname or None if not SSH/mosh

    Examples:
        >>> parse_ssh_host("ssh user@example.com")
        'example.com'
        >>> parse_ssh_host("ssh -i ~/.ssh/key -p 2222 server.local")
        'server.local'
        >>> parse_ssh_host("mosh user@10.0.0.1")
        '10.0.0.1'
        >>> parse_ssh_host("ssh [::1]")
        '::1'
    """
    # Convert string to list if needed
    if isinstance(cmdline, str):
        argv = cmdline.split()
    else:
        argv = list(cmdline)

    if not argv:
        return None

    # Check if this is an SSH-like command
    prog = os.path.basename(argv[0])
    if prog not in ("ssh", "slogin", "mosh", "mosh-client"):
        return None

    args = argv[1:]

    # Find first non-option argument (the hostname)
    host = _take_first_non_option(args)
    if not host:
        return None

    # Normalize the hostname
    return _normalize_hostname(host)


def _take_first_non_option(args: list[str]) -> str | None:
    """Extract first non-option argument, skipping flags and their values."""
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--":
            # Everything after -- is positional
            if i + 1 < len(args):
                return args[i + 1]
            return None

        if arg.startswith("-"):
            # Check if this option takes an argument
            if arg in _SSH_OPTIONS_WITH_ARG:
                # Skip the option and its argument
                i += 2
                continue
            # Could be combined like -i/path/to/key
            for opt in _SSH_OPTIONS_WITH_ARG:
                if arg.startswith(opt):
                    # Argument is attached, just skip this one
                    i += 1
                    break
            else:
                # Regular flag without argument
                i += 1
            continue

        # Found a non-option argument
        return arg

    return None


def _normalize_hostname(host: str) -> str:
    """
    Normalize hostname by stripping user@, brackets, and port.

    Examples:
        user@host -> host
        [::1] -> ::1
        host:22 -> host
        user@[::1]:22 -> ::1
    """
    # Strip user@ prefix
    if "@" in host:
        host = host.split("@", 1)[1]

    # Handle IPv6 brackets
    if host.startswith("["):
        # Find closing bracket
        bracket_end = host.find("]")
        if bracket_end > 0:
            host = host[1:bracket_end]
        else:
            host = host[1:]  # Malformed, strip leading [
    elif ":" in host:
        # IPv4 with port - strip port
        # But not IPv6 (already handled above)
        host = host.split(":", 1)[0]

    return host.lower()
```

## Getting Command Line from tmux

The caller (icon_resolver.py) will get the foreground command from tmux:

```python
def get_pane_foreground_cmdline(pane_pid: int) -> list[str]:
    """Get command line of foreground process in pane."""
    try:
        # Get foreground process group
        with open(f"/proc/{pane_pid}/stat") as f:
            stat = f.read()
        # Field 8 is tpgid (foreground process group)
        fields = stat.split()
        tpgid = int(fields[7])

        # Read cmdline of that process
        with open(f"/proc/{tpgid}/cmdline") as f:
            cmdline = f.read()

        return cmdline.split("\0")[:-1]  # Remove trailing empty
    except (OSError, IndexError, ValueError):
        return []
```

## CLI Interface

```bash
# Parse from command string
python3 scripts/ssh_parser.py "ssh user@example.com"
# Output: example.com

# Parse from tmux pane
python3 scripts/ssh_parser.py --pane-pid 12345
# Output: (hostname if SSH detected, empty otherwise)

# Exit codes:
# 0 = SSH detected, hostname printed
# 1 = Not an SSH command
# 2 = Error
```

## Implementation

```python
#!/usr/bin/env python3
"""
ssh_parser.py - Extract SSH/mosh target hostname from command lines.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_SSH_OPTIONS_WITH_ARG = frozenset((
    "-b", "-c", "-D", "-E", "-F", "-I", "-i", "-J", "-L", "-l",
    "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w", "-B",
))


def parse_ssh_host(cmdline: str | Sequence[str]) -> str | None:
    """Parse SSH/mosh command line to extract target hostname."""
    if isinstance(cmdline, str):
        argv = cmdline.split()
    else:
        argv = list(cmdline)

    if not argv:
        return None

    prog = os.path.basename(argv[0])
    if prog not in ("ssh", "slogin", "mosh", "mosh-client"):
        return None

    host = _take_first_non_option(argv[1:])
    if not host:
        return None

    return _normalize_hostname(host)


def _take_first_non_option(args: list[str]) -> str | None:
    """Extract first non-option argument."""
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--":
            return args[i + 1] if i + 1 < len(args) else None

        if arg.startswith("-"):
            if arg in _SSH_OPTIONS_WITH_ARG:
                i += 2
                continue
            for opt in _SSH_OPTIONS_WITH_ARG:
                if arg.startswith(opt):
                    i += 1
                    break
            else:
                i += 1
            continue

        return arg

    return None


def _normalize_hostname(host: str) -> str:
    """Normalize hostname by stripping user@, brackets, and port."""
    if "@" in host:
        host = host.split("@", 1)[1]

    if host.startswith("["):
        bracket_end = host.find("]")
        if bracket_end > 0:
            host = host[1:bracket_end]
        else:
            host = host[1:]
    elif ":" in host:
        host = host.split(":", 1)[0]

    return host.lower()


def get_foreground_cmdline(pane_pid: int) -> list[str]:
    """Get command line of foreground process in pane."""
    try:
        with open(f"/proc/{pane_pid}/stat") as f:
            stat = f.read()
        fields = stat.split()
        tpgid = int(fields[7])

        with open(f"/proc/{tpgid}/cmdline") as f:
            cmdline = f.read()

        return cmdline.split("\0")[:-1]
    except (OSError, IndexError, ValueError):
        return []


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: ssh_parser.py <cmdline> | --pane-pid <pid>", file=sys.stderr)
        return 2

    if sys.argv[1] == "--pane-pid":
        if len(sys.argv) < 3:
            print("Error: --pane-pid requires PID argument", file=sys.stderr)
            return 2
        try:
            pid = int(sys.argv[2])
        except ValueError:
            print(f"Error: Invalid PID: {sys.argv[2]}", file=sys.stderr)
            return 2
        cmdline = get_foreground_cmdline(pid)
    else:
        cmdline = " ".join(sys.argv[1:])

    host = parse_ssh_host(cmdline)
    if host:
        print(host)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

## Testing

```python
def test_simple_ssh():
    assert parse_ssh_host("ssh example.com") == "example.com"

def test_ssh_with_user():
    assert parse_ssh_host("ssh user@example.com") == "example.com"

def test_ssh_with_options():
    assert parse_ssh_host("ssh -i ~/.ssh/key -p 2222 server") == "server"

def test_ssh_combined_option():
    assert parse_ssh_host("ssh -i~/.ssh/key host") == "host"

def test_mosh():
    assert parse_ssh_host("mosh user@remote.host") == "remote.host"

def test_ipv6():
    assert parse_ssh_host("ssh [::1]") == "::1"

def test_ipv6_with_port():
    assert parse_ssh_host("ssh [2001:db8::1]:22") == "2001:db8::1"

def test_not_ssh():
    assert parse_ssh_host("vim file.txt") is None
    assert parse_ssh_host("nvim") is None
```

## Linting

```bash
ruff check scripts/ssh_parser.py
ruff format --check scripts/ssh_parser.py
mypy --strict scripts/ssh_parser.py
```

## Reference

Pattern follows `/home/rain/.config/kitty/tab_bar.py` lines 627-670.
