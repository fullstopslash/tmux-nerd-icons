#!/usr/bin/env python3
"""Parse SSH/mosh command lines to extract target hostnames.

This module provides utilities to parse SSH and mosh command lines,
extract the target hostname, and normalize it for host-specific icon matching.

Example usage:
    >>> from ssh_parser import parse_ssh_host
    >>> parse_ssh_host("ssh user@example.com")
    'example.com'
    >>> parse_ssh_host("ssh -i ~/.ssh/key -p 2222 server.local")
    'server.local'

Copyright (C) 2025 Rain

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# SSH/mosh command names that we recognize
_SSH_COMMANDS: frozenset[str] = frozenset(("ssh", "slogin", "mosh", "mosh-client"))

# SSH options that consume the next argument as their value.
# These must be skipped along with their argument when searching for the hostname.
_SSH_OPTIONS_WITH_ARG: frozenset[str] = frozenset(
    (
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
    )
)


def parse_ssh_host(cmdline: str | Sequence[str]) -> str | None:
    """Parse SSH/mosh command line to extract the target hostname.

    This function accepts either a string command line or a sequence of
    arguments (e.g., from /proc/<pid>/cmdline). It recognizes ssh, slogin,
    mosh, and mosh-client commands.

    Args:
        cmdline: Command line as a string (space-separated) or sequence
            of arguments.

    Returns:
        Normalized lowercase hostname, or None if not an SSH/mosh command
        or if no hostname could be extracted.

    Examples:
        >>> parse_ssh_host("ssh example.com")
        'example.com'
        >>> parse_ssh_host("ssh user@example.com")
        'example.com'
        >>> parse_ssh_host("ssh -i ~/.ssh/key -p 2222 server.local")
        'server.local'
        >>> parse_ssh_host("mosh user@10.0.0.1")
        '10.0.0.1'
        >>> parse_ssh_host("ssh [::1]")
        '::1'
        >>> parse_ssh_host("vim file.txt") is None
        True
    """
    # Convert string to list if needed
    argv = cmdline.split() if isinstance(cmdline, str) else list(cmdline)

    if not argv:
        return None

    # Check if this is an SSH-like command
    prog = os.path.basename(argv[0])
    if prog not in _SSH_COMMANDS:
        return None

    # Find the first non-option argument (the hostname)
    host = _take_first_non_option(argv[1:])
    if not host:
        return None

    return _normalize_hostname(host)


def _take_first_non_option(args: list[str]) -> str | None:
    """Extract the first non-option argument from an argument list.

    This function skips SSH options and their associated values to find
    the first positional argument (the hostname).

    Args:
        args: List of command arguments (excluding the program name).

    Returns:
        The first non-option argument, or None if no positional argument
        is found.

    Examples:
        >>> _take_first_non_option(["example.com"])
        'example.com'
        >>> _take_first_non_option(["-i", "key", "-p", "22", "host"])
        'host'
        >>> _take_first_non_option(["-v", "-A", "server"])
        'server'
        >>> _take_first_non_option(["--", "host"])
        'host'
    """
    i = 0
    while i < len(args):
        arg = args[i]

        # Handle -- (end of options marker)
        if arg == "--":
            # Everything after -- is positional
            return args[i + 1] if i + 1 < len(args) else None

        if arg.startswith("-"):
            # Check if this option takes an argument
            if arg in _SSH_OPTIONS_WITH_ARG:
                # Skip the option and its argument
                i += 2
                continue

            # Check for combined option+value (e.g., -i/path/to/key or -p22)
            for opt in _SSH_OPTIONS_WITH_ARG:
                if arg.startswith(opt) and len(arg) > len(opt):
                    # Argument is attached to option, just skip this one
                    i += 1
                    break
            else:
                # Regular flag without argument (e.g., -v, -A, -X)
                i += 1
            continue

        # Found a non-option argument (the hostname)
        return arg

    return None


def _normalize_hostname(host: str) -> str:
    """Normalize a hostname by stripping user@, IPv6 brackets, and port.

    Args:
        host: Raw hostname that may include user prefix, brackets, or port.

    Returns:
        Normalized lowercase hostname.

    Examples:
        >>> _normalize_hostname("user@host")
        'host'
        >>> _normalize_hostname("[::1]")
        '::1'
        >>> _normalize_hostname("host:22")
        'host'
        >>> _normalize_hostname("user@[2001:db8::1]:22")
        '2001:db8::1'
        >>> _normalize_hostname("Example.COM")
        'example.com'
    """
    # Strip user@ prefix
    if "@" in host:
        host = host.split("@", 1)[1]

    # Strip whitespace
    host = host.strip()

    # Handle IPv6 addresses in brackets
    if host.startswith("["):
        bracket_end = host.find("]")
        # Extract IPv6 address from brackets, or strip leading [ if malformed
        host = host[1:bracket_end] if bracket_end > 0 else host[1:]
    elif ":" in host:
        # IPv4 with port suffix - strip port
        # Note: IPv6 without brackets would also have colons, but that's
        # technically malformed SSH syntax; we handle it gracefully by
        # only stripping what looks like host:port
        host = host.split(":", 1)[0]

    return host.lower()


def get_foreground_cmdline(pane_pid: int) -> list[str]:
    """Get the command line of the foreground process in a tmux pane.

    This function reads the foreground process group ID from /proc/<pid>/stat
    and then retrieves the command line of that process.

    Args:
        pane_pid: The PID of the tmux pane's shell process.

    Returns:
        List of command-line arguments, or empty list on error.

    Note:
        This function is Linux-specific and requires /proc filesystem access.
    """
    try:
        # Read the stat file to get the foreground process group ID
        stat_path = f"/proc/{pane_pid}/stat"
        with open(stat_path, encoding="utf-8") as f:
            stat_content = f.read()

        # Field 8 (0-indexed: 7) is tpgid (foreground process group ID)
        # The format is: pid (comm) state ppid pgrp session tty_nr tpgid ...
        # We need to handle the case where comm contains spaces or parentheses
        fields = stat_content.split()
        tpgid = int(fields[7])

        # Read the command line of the foreground process
        cmdline_path = f"/proc/{tpgid}/cmdline"
        with open(cmdline_path, encoding="utf-8", errors="replace") as f:
            cmdline_content = f.read()

        # cmdline is NUL-separated; split and remove trailing empty string
        parts = cmdline_content.split("\0")
        # Remove empty strings (last element is always empty after split)
        return [p for p in parts if p]

    except (OSError, IndexError, ValueError):
        # File not found, permission denied, process terminated, etc.
        return []


def main() -> int:
    """CLI entry point for ssh_parser.

    Usage:
        python3 ssh_parser.py "ssh user@example.com"
        python3 ssh_parser.py --pane-pid 12345

    Exit codes:
        0: SSH detected, hostname printed to stdout
        1: Not an SSH command (or no hostname found)
        2: Usage error
    """
    if len(sys.argv) < 2:
        print(
            "Usage: ssh_parser.py <cmdline> | --pane-pid <pid>",
            file=sys.stderr,
        )
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
        cmdline: str | list[str] = get_foreground_cmdline(pid)
    else:
        # Join all remaining arguments as the command line string
        cmdline = " ".join(sys.argv[1:])

    host = parse_ssh_host(cmdline)
    if host:
        print(host)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
