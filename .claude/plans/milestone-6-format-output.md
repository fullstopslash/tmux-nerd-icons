# Milestone 6: Format Output

**Target File:** `/home/rain/projects/tmux-nerd-icons/scripts/format_output.sh`

**Dependencies:** Milestone 2 (helpers.sh), Milestone 5 (icon_resolver.py)

## Purpose

Generate the final formatted output for tmux window names, including ring symbols,
icons, optional colors, and multi-pane indicators.

## Requirements

1. Bash script (shellcheck compliant)
2. Generate ring symbols based on window index
3. Call icon_resolver.py for icon lookup
4. Apply tmux color format strings
5. Handle multi-pane indicator
6. Support optional window name display

## Ring Symbols

10 rotating symbols for window indices 0-9, then wrapping:

```bash
RING_SYMBOLS=(
    "󰬺"  # 0
    "󰬻"  # 1
    "󰬼"  # 2
    "󰬽"  # 3
    "󰬾"  # 4
    "󰬿"  # 5
    "󰭀"  # 6
    "󰭁"  # 7
    "󰭂"  # 8
    "󰿩"  # 9
)
```

## Interface

```bash
scripts/format_output.sh \
    --process "nvim" \
    --title "README.md" \
    --session "code" \
    --index "2" \
    --panes "1" \
    --active "1"

# Output (with colors):
# #[fg=#875fff]󰬼#[fg=#cdd6f4] #[default]

# Output (simple, no colors):
# 󰬼
```

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--process` | Pane current command | `nvim` |
| `--title` | Pane title | `README.md` |
| `--session` | Session name | `code` |
| `--index` | Window index (0-based) | `2` |
| `--panes` | Number of panes in window | `3` |
| `--active` | Is window active (1/0) | `1` |
| `--show-name` | Show window name with icon | (flag) |
| `--pane-pid` | Pane PID for SSH detection | `12345` |

## Implementation

```bash
#!/usr/bin/env bash
# format_output.sh - Format tmux window name with ring symbol and icon
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

# Ring symbols for window indices
RING_SYMBOLS=(
    "󰬺" "󰬻" "󰬼" "󰬽" "󰬾"
    "󰬿" "󰭀" "󰭁" "󰭂" "󰿩"
)

# Default colors (can be overridden by config)
DEFAULT_RING_ACTIVE="#875fff"
DEFAULT_RING_INACTIVE="#45475a"
DEFAULT_ICON_COLOR="#cdd6f4"

# Parse arguments
process=""
title=""
session=""
index=0
panes=1
active=0
show_name=0
pane_pid=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --process)
            process="$2"
            shift 2
            ;;
        --title)
            title="$2"
            shift 2
            ;;
        --session)
            session="$2"
            shift 2
            ;;
        --index)
            index="$2"
            shift 2
            ;;
        --panes)
            panes="$2"
            shift 2
            ;;
        --active)
            active="$2"
            shift 2
            ;;
        --show-name)
            show_name=1
            shift
            ;;
        --pane-pid)
            pane_pid="$2"
            shift 2
            ;;
        *)
            log_error "Unknown argument: $1"
            shift
            ;;
    esac
done

# Get ring symbol for index
get_ring_symbol() {
    local idx="$1"
    local ring_idx=$((idx % ${#RING_SYMBOLS[@]}))
    echo "${RING_SYMBOLS[$ring_idx]}"
}

# Get icon from Python resolver
get_icon() {
    local python
    python=$(get_python) || {
        log_error "Python 3 not found"
        echo "󰽙"  # Fallback
        return
    }

    local config_path
    config_path=$(get_config_path)

    local args=(
        "$SCRIPT_DIR/icon_resolver.py"
        --simple
        --config "$config_path"
    )

    [[ -n "$process" ]] && args+=(--process "$process")
    [[ -n "$title" ]] && args+=(--title "$title")
    [[ -n "$session" ]] && args+=(--session "$session")
    [[ -n "$pane_pid" ]] && args+=(--pane-pid "$pane_pid")

    "$python" "${args[@]}" 2>/dev/null || echo "󰽙"
}

# Get icon with colors (JSON mode)
get_icon_with_colors() {
    local python
    python=$(get_python) || {
        echo '{"icon":"󰽙"}'
        return
    }

    local config_path
    config_path=$(get_config_path)

    local args=(
        "$SCRIPT_DIR/icon_resolver.py"
        --config "$config_path"
    )

    [[ -n "$process" ]] && args+=(--process "$process")
    [[ -n "$title" ]] && args+=(--title "$title")
    [[ -n "$session" ]] && args+=(--session "$session")
    [[ -n "$pane_pid" ]] && args+=(--pane-pid "$pane_pid")

    "$python" "${args[@]}" 2>/dev/null || echo '{"icon":"󰽙"}'
}

# Format output with colors
format_with_colors() {
    local ring_sym="$1"
    local icon="$2"
    local ring_color="$3"
    local icon_color="$4"
    local name="$5"

    local output=""

    # Ring symbol with color
    if [[ -n "$ring_color" ]]; then
        output+="#[fg=${ring_color}]${ring_sym}#[default]"
    else
        output+="${ring_sym}"
    fi

    # Space + Icon with color
    if [[ -n "$icon_color" ]]; then
        output+="#[fg=${icon_color}] ${icon}#[default]"
    else
        output+=" ${icon}"
    fi

    # Optional name
    if [[ -n "$name" ]]; then
        output+=" ${name}"
    fi

    echo "$output"
}

# Main
main() {
    local ring_sym
    ring_sym=$(get_ring_symbol "$index")

    # Get icon (simple mode for now, could use JSON for colors)
    local icon
    icon=$(get_icon)

    # Determine ring color based on active state
    local ring_color
    if [[ "$active" == "1" ]]; then
        ring_color="$DEFAULT_RING_ACTIVE"
    else
        ring_color="$DEFAULT_RING_INACTIVE"
    fi

    # Multi-pane indicator
    local multi_pane_prefix=""
    if [[ "$panes" -gt 1 ]]; then
        # Could add a multi-pane icon here
        # multi_pane_prefix="󰕰 "
        :
    fi

    # Optional window name
    local name=""
    if [[ "$show_name" == "1" && -n "$title" ]]; then
        # Truncate long names
        if [[ ${#title} -gt 20 ]]; then
            name="${title:0:17}…"
        else
            name="$title"
        fi
    fi

    # Format and output
    format_with_colors "$ring_sym" "${multi_pane_prefix}${icon}" "$ring_color" "$DEFAULT_ICON_COLOR" "$name"
}

main
```

## Simple Mode (No Colors)

For environments that don't support tmux format colors:

```bash
format_simple() {
    local ring_sym="$1"
    local icon="$2"
    local name="$3"

    if [[ -n "$name" ]]; then
        echo "${ring_sym} ${icon} ${name}"
    else
        echo "${ring_sym} ${icon}"
    fi
}
```

## Testing

```bash
# Test ring symbols
for i in {0..12}; do
    ./scripts/format_output.sh --process zsh --index "$i" --panes 1 --active 1
done

# Test with different processes
./scripts/format_output.sh --process nvim --title "file.py" --index 0 --active 1
./scripts/format_output.sh --process firefox --title "GitHub" --index 1 --active 0

# Test multi-pane
./scripts/format_output.sh --process zsh --index 0 --panes 3 --active 1
```

## Linting

```bash
shellcheck scripts/format_output.sh
```

## Integration with tmux

The output is used in `automatic-rename-format`:

```bash
# In nerd-icons.tmux:
tmux set-option -g automatic-rename-format \
    "#($PLUGIN_DIR/scripts/format_output.sh \
        --process '#{pane_current_command}' \
        --title '#{pane_title}' \
        --session '#{session_name}' \
        --index '#{window_index}' \
        --panes '#{window_panes}' \
        --active '#{window_active}' \
        --pane-pid '#{pane_pid}')"
```

## Performance Notes

- Script is called frequently (on each window rename event)
- Python invocation is the slowest part
- Consider caching or daemon mode for high-frequency updates
- Keep shell overhead minimal
