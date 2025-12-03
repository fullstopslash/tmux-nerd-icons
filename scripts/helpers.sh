#!/usr/bin/env bash
# helpers.sh - Shared utilities for tmux-nerd-icons
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# Prevent double-sourcing
if [[ -n "${_NERD_ICONS_HELPERS_LOADED:-}" ]]; then
    return 0
fi
_NERD_ICONS_HELPERS_LOADED=1

# Get the scripts directory and plugin root
# NOTE: Uses BASH_SOURCE which is a bash-specific feature
NERD_ICONS_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly NERD_ICONS_SCRIPTS_DIR
export NERD_ICONS_SCRIPTS_DIR

NERD_ICONS_PLUGIN_DIR="$(dirname "${NERD_ICONS_SCRIPTS_DIR}")"
readonly NERD_ICONS_PLUGIN_DIR
export NERD_ICONS_PLUGIN_DIR

# get_tmux_option - Read a tmux option with fallback default
#
# Usage: get_tmux_option "option_name" "default_value"
# Returns: option value or default
#
# Example:
#   value=$(get_tmux_option "@my_option" "default")
#
get_tmux_option() {
    local option="$1"
    local default_value="$2"
    local option_value

    option_value=$(tmux show-option -gqv "${option}" 2>/dev/null)

    if [[ -n "${option_value}" ]]; then
        echo "${option_value}"
    else
        echo "${default_value}"
    fi
}

# get_config_path - Resolve configuration file path with precedence
#
# Precedence order:
#   1. $NERD_ICONS_CONFIG environment variable
#   2. @nerd_icons_config tmux option
#   3. ~/.config/nerd-icons/config.yml (default)
#
# Usage: config_path=$(get_config_path)
#
get_config_path() {
    if [[ -n "${NERD_ICONS_CONFIG:-}" ]]; then
        echo "${NERD_ICONS_CONFIG}"
        return
    fi

    local tmux_config
    tmux_config=$(get_tmux_option "@nerd_icons_config" "")
    if [[ -n "${tmux_config}" ]]; then
        echo "${tmux_config}"
        return
    fi

    echo "${HOME}/.config/nerd-icons/config.yml"
}

# command_exists - Check if a command is available
#
# Usage: if command_exists python3; then ...; fi
#
# Returns: 0 if command exists, 1 otherwise
#
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# get_python - Find Python 3 interpreter
#
# Usage: python_cmd=$(get_python)
#
# Returns: "python3" or "python" if Python 3 is available, empty string otherwise
# Exit code: 0 if found, 1 if not found
#
get_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        # Verify it's Python 3
        if python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
            echo "python"
        else
            return 1
        fi
    else
        return 1
    fi
}

# log_error - Log errors to stderr with prefix
#
# Usage: log_error "Something went wrong"
#
log_error() {
    echo "[nerd-icons] ERROR: $*" >&2
}

# log_warn - Log warnings to stderr with prefix
#
# Usage: log_warn "This is deprecated"
#
log_warn() {
    echo "[nerd-icons] WARN: $*" >&2
}

# log_debug - Log debug messages to stderr (only if NERD_ICONS_DEBUG=1)
#
# Usage: log_debug "Variable value: $var"
#
# Enable debug output with: export NERD_ICONS_DEBUG=1
#
log_debug() {
    if [[ "${NERD_ICONS_DEBUG:-}" = "1" ]]; then
        echo "[nerd-icons] DEBUG: $*" >&2
    fi
}
