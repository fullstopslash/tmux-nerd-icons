# Milestone 1: TPM Entry Point

**Target File:** `/home/rain/projects/tmux-nerd-icons/nerd-icons.tmux`

**Dependencies:** Milestone 2, Milestone 6 (must be completed first)

## Purpose

TPM-compatible plugin entry point that integrates with tmux's window naming system.

## Requirements

1. Set executable permissions on all scripts
2. Configure `automatic-rename on`
3. Set `automatic-rename-format` to call format_output.sh
4. Support optional `@nerd_icons_*` user options

## Interface

Called by TPM when plugin is loaded. Must be executable.

## Implementation

```bash
#!/usr/bin/env bash
# nerd-icons.tmux - TPM entry point for tmux-nerd-icons
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$CURRENT_DIR/scripts/helpers.sh"

main() {
    # Enable automatic renaming
    tmux set-option -g automatic-rename on

    # Get user options or defaults
    local show_name
    show_name=$(get_tmux_option "@nerd_icons_show_name" "")

    # Build format string
    local format_cmd="$CURRENT_DIR/scripts/format_output.sh"
    format_cmd+=" --process '#{pane_current_command}'"
    format_cmd+=" --title '#{pane_title}'"
    format_cmd+=" --session '#{session_name}'"
    format_cmd+=" --index '#{window_index}'"
    format_cmd+=" --panes '#{window_panes}'"
    format_cmd+=" --active '#{window_active}'"

    if [ -n "$show_name" ]; then
        format_cmd+=" --show-name"
    fi

    # Set the format
    tmux set-option -g automatic-rename-format "#($format_cmd)"
}

main
```

## User Options

| Option | Description | Default |
|--------|-------------|---------|
| `@nerd_icons_show_name` | Show window name with icon | (from config) |
| `@nerd_icons_config` | Override config path | `~/.config/nerd-icons/config.yml` |

## Testing

```bash
# Manual test after installation
tmux source ~/.tmux.conf
# Should see icons in window names
```

## Linting

```bash
shellcheck nerd-icons.tmux
```
