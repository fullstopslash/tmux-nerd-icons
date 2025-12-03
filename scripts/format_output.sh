#!/usr/bin/env bash
# format_output.sh - Format tmux window name with ring symbol and icon
#
# This file is part of tmux-nerd-icons.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

set -euo pipefail

# Determine script directory and source helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

# Source helper utilities
# shellcheck source=scripts/helpers.sh
source "${SCRIPT_DIR}/helpers.sh"

# Ring symbols for window indices (0-9, then wraps)
# These are Nerd Font symbols that create a rotating visual indicator
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
readonly RING_SYMBOLS

# Default colors (Catppuccin Mocha palette)
# These can be overridden by tmux options or config file in the future
DEFAULT_RING_ACTIVE="#875fff"      # Active window ring color (purple)
DEFAULT_RING_INACTIVE="#45475a"    # Inactive window ring color (dark gray)
DEFAULT_ICON_COLOR="#cdd6f4"       # Default icon color (light gray)
readonly DEFAULT_RING_ACTIVE
readonly DEFAULT_RING_INACTIVE
readonly DEFAULT_ICON_COLOR

# Parse command-line arguments
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
            exit 1
            ;;
    esac
done

# get_ring_symbol - Get ring symbol for window index
#
# Uses modulo arithmetic to map any window index to one of 10 ring symbols.
# This creates a repeating visual pattern that helps distinguish windows.
#
# Args:
#   $1 - Window index (0-based)
#
# Returns:
#   Ring symbol character
#
get_ring_symbol() {
    local idx="$1"
    local ring_idx=$((idx % ${#RING_SYMBOLS[@]}))
    echo "${RING_SYMBOLS[${ring_idx}]}"
}

# get_icon - Get icon from Python resolver (simple mode)
#
# Calls icon_resolver.py to determine the appropriate icon based on
# process name, title, session, and optional SSH detection via PID.
#
# Returns:
#   Icon character, or fallback icon on error
#
get_icon() {
    local python
    # Disable errexit temporarily for proper error handling
    set +e
    python=$(get_python)
    local get_python_result=$?
    set -e

    if [[ ${get_python_result} -ne 0 ]]; then
        log_error "Python 3 not found"
        echo "󰽙"  # Fallback icon
        return
    fi

    local config_path
    config_path=$(get_config_path)

    local args=(
        "${SCRIPT_DIR}/icon_resolver.py"
        --simple
        --config "${config_path}"
    )

    [[ -n "${process}" ]] && args+=(--process "${process}")
    [[ -n "${title}" ]] && args+=(--title "${title}")
    [[ -n "${session}" ]] && args+=(--session "${session}")
    [[ -n "${pane_pid}" ]] && args+=(--pane-pid "${pane_pid}")

    "${python}" "${args[@]}" 2>/dev/null || echo "󰽙"
}

# get_icon_with_colors - Get icon with color metadata (JSON mode)
#
# Like get_icon, but returns full JSON response including icon colors.
# This is for future enhancement to support per-icon color configuration.
#
# Returns:
#   JSON object with icon and optional color fields
#
get_icon_with_colors() {
    local python
    # Disable errexit temporarily for proper error handling
    set +e
    python=$(get_python)
    local get_python_result=$?
    set -e

    if [[ ${get_python_result} -ne 0 ]]; then
        echo '{"icon":"󰽙"}'
        return
    fi

    local config_path
    config_path=$(get_config_path)

    local args=(
        "${SCRIPT_DIR}/icon_resolver.py"
        --config "${config_path}"
    )

    [[ -n "${process}" ]] && args+=(--process "${process}")
    [[ -n "${title}" ]] && args+=(--title "${title}")
    [[ -n "${session}" ]] && args+=(--session "${session}")
    [[ -n "${pane_pid}" ]] && args+=(--pane-pid "${pane_pid}")

    "${python}" "${args[@]}" 2>/dev/null || echo '{"icon":"󰽙"}'
}

# format_with_colors - Build tmux format string with colors
#
# Constructs the final output string with tmux color escape sequences.
# The format is: [ring_color]RING[icon_color] ICON[default] [NAME]
#
# Args:
#   $1 - Ring symbol
#   $2 - Icon character
#   $3 - Ring color (hex)
#   $4 - Icon color (hex)
#   $5 - Optional window name
#
# Returns:
#   Tmux-formatted string with color codes
#
format_with_colors() {
    local ring_sym="$1"
    local icon="$2"
    local ring_color="$3"
    local icon_color="$4"
    local name="$5"

    local output=""

    # Ring symbol with color
    if [[ -n "${ring_color}" ]]; then
        output+="#[fg=${ring_color}]${ring_sym}#[default]"
    else
        output+="${ring_sym}"
    fi

    # Space + Icon with color
    if [[ -n "${icon_color}" ]]; then
        output+="#[fg=${icon_color}] ${icon}#[default]"
    else
        output+=" ${icon}"
    fi

    # Optional window name
    if [[ -n "${name}" ]]; then
        output+=" ${name}"
    fi

    echo "${output}"
}

# format_simple - Build simple output without colors
#
# For environments that don't support or need tmux color codes.
# Just outputs the symbols and optional name.
#
# Args:
#   $1 - Ring symbol
#   $2 - Icon character
#   $3 - Optional window name
#
# Returns:
#   Plain text string
#
format_simple() {
    local ring_sym="$1"
    local icon="$2"
    local name="$3"

    if [[ -n "${name}" ]]; then
        echo "${ring_sym} ${icon} ${name}"
    else
        echo "${ring_sym} ${icon}"
    fi
}

# Main execution
main() {
    # Get ring symbol based on window index
    local ring_sym
    ring_sym=$(get_ring_symbol "${index}")

    # Get icon from resolver (simple mode for now)
    # Future: could use JSON mode to extract per-icon colors
    local icon
    icon=$(get_icon)

    # Determine ring color based on window active state
    local ring_color
    if [[ "${active}" == "1" ]]; then
        ring_color="${DEFAULT_RING_ACTIVE}"
    else
        ring_color="${DEFAULT_RING_INACTIVE}"
    fi

    # Multi-pane indicator (reserved for future enhancement)
    # Could add a visual indicator for windows with multiple panes
    local multi_pane_prefix=""
    if [[ "${panes}" -gt 1 ]]; then
        # Uncomment to add multi-pane indicator:
        # multi_pane_prefix="󰕰 "
        :
    fi

    # Optional window name display
    local name=""
    if [[ "${show_name}" == "1" && -n "${title}" ]]; then
        # Truncate long names to prevent overwhelming the status bar
        if [[ ${#title} -gt 20 ]]; then
            name="${title:0:17}…"
        else
            name="${title}"
        fi
    fi

    # Format and output
    # Check if we should use simple mode (no colors)
    # This could be controlled by a config option in the future
    local use_colors=1

    if [[ "${use_colors}" == "1" ]]; then
        format_with_colors "${ring_sym}" "${multi_pane_prefix}${icon}" "${ring_color}" "${DEFAULT_ICON_COLOR}" "${name}"
    else
        format_simple "${ring_sym}" "${multi_pane_prefix}${icon}" "${name}"
    fi
}

main
