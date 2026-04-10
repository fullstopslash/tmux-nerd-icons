"""CLI entry point for nerd-icons (tmux-nerd-icons edition).

Extends the core resolver with tmux-specific features:
- SSH hostname detection via --pane-pid (reads /proc)
- multi_pane_icon from config
- --session-only mode

Usage:
    python -m nerd_icons --process zsh --title "~" --session main --tsv
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .cache import get_config
from .resolver import resolve_icon
from .ssh import get_foreground_cmdline, parse_ssh_host


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Resolve nerd font icon for a tmux window context",
    )
    parser.add_argument("--process", "-p", default="", help="Process name")
    parser.add_argument("--title", "-t", default="", help="Window/pane title")
    parser.add_argument("--session", "-s", default="", help="Session name")
    parser.add_argument("--hostname", default="", help="SSH hostname (if known)")
    parser.add_argument("--config", default="~/.config/nerd-icons/config.yml", help="Config path")
    parser.add_argument("--pane-pid", type=int, default=None, help="Pane PID for SSH detection")
    parser.add_argument("--session-only", action="store_true", help="Only resolve session icon")

    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--tsv", action="store_true", help="Output as TSV (icon, multi_pane_icon)")
    output_mode.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        config = get_config(args.config)

        # Session-only mode: skip process/title/host, just resolve session
        if args.session_only:
            result = resolve_icon(
                session=args.session,
                config=config,
            )
            # In session-only mode, only session and fallback should match
            # (process/title/host inputs are intentionally omitted)
        else:
            # Detect SSH hostname from pane PID if not provided
            hostname = args.hostname
            if not hostname and args.pane_pid is not None:
                cmdline_parts = get_foreground_cmdline(args.pane_pid)
                if cmdline_parts:
                    detected = parse_ssh_host(cmdline_parts)
                    if detected:
                        hostname = detected

            result = resolve_icon(
                process=args.process,
                title=args.title,
                session=args.session,
                hostname=hostname,
                config=config,
            )

        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False))
        elif args.tsv:
            multi_pane = config.config.multi_pane_icon or ""
            print(f"{result.icon}\t{multi_pane}")
        else:
            print(result.icon)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
