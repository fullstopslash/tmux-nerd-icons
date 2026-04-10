"""SSH/mosh command line parsing for hostname extraction.

Detects ssh, slogin, mosh, and mosh-client commands. Parses the command
line to extract and normalize the target hostname.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# SSH/mosh command names
_SSH_COMMANDS: frozenset[str] = frozenset(("ssh", "slogin", "mosh", "mosh-client"))

# SSH options that consume the next argument
_SSH_OPTIONS_WITH_ARG: frozenset[str] = frozenset((
    "-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J",
    "-L", "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S",
    "-W", "-w", "-B",
))


def parse_ssh_host(cmdline: str | Sequence[str]) -> str | None:
    """Parse SSH/mosh command line to extract the target hostname.

    Args:
        cmdline: Command line as a string or sequence of arguments.

    Returns:
        Normalized lowercase hostname, or None if not an SSH/mosh command.
    """
    argv = cmdline.split() if isinstance(cmdline, str) else list(cmdline)

    if not argv:
        return None

    prog = os.path.basename(argv[0])
    if prog not in _SSH_COMMANDS:
        return None

    host = _take_first_non_option(argv[1:])
    if not host:
        return None

    return _normalize_hostname(host)


def _take_first_non_option(args: list[str]) -> str | None:
    """Extract the first non-option argument from an argument list."""
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--":
            return args[i + 1] if i + 1 < len(args) else None

        if arg.startswith("-"):
            if arg in _SSH_OPTIONS_WITH_ARG:
                i += 2
                continue

            if len(arg) > 2 and arg[:2] in _SSH_OPTIONS_WITH_ARG:
                i += 1
            else:
                i += 1
            continue

        return arg

    return None


def _normalize_hostname(host: str) -> str | None:
    """Normalize a hostname by stripping user@, IPv6 brackets, and port.

    Returns:
        Normalized lowercase hostname, or None if empty.
    """
    if "@" in host:
        host = host.split("@", 1)[1]

    host = host.strip()

    if host.startswith("["):
        bracket_end = host.find("]")
        host = host[1:bracket_end] if bracket_end > 0 else host[1:]
    elif host.count(":") == 1:
        host = host.split(":", 1)[0]

    return host.lower() or None


def get_foreground_cmdline(pane_pid: int) -> list[str]:
    """Get the command line of the foreground process in a pane.

    Reads from /proc/<pid>/stat to get tpgid, then reads
    /proc/<tpgid>/cmdline. Linux-specific.

    Args:
        pane_pid: PID of the shell process.

    Returns:
        List of command-line arguments, or empty list on error.
    """
    try:
        stat_path = f"/proc/{pane_pid}/stat"
        with open(stat_path, encoding="utf-8", errors="replace") as f:
            stat_content = f.read()

        close_paren = stat_content.rfind(")")
        rest = stat_content[close_paren + 2:]
        rest_fields = rest.split()
        tpgid = int(rest_fields[5])

        cmdline_path = f"/proc/{tpgid}/cmdline"
        with open(cmdline_path, encoding="utf-8", errors="replace") as f:
            cmdline_content = f.read()

        parts = cmdline_content.split("\0")
        return [p for p in parts if p]

    except (OSError, IndexError, ValueError):
        return []
