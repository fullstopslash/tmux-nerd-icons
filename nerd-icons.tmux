#!/usr/bin/env bash
# nerd-icons.tmux - TPM entry point for tmux-nerd-icons
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/helpers.sh
source "${CURRENT_DIR}/scripts/helpers.sh"

main() {
    # Enable automatic renaming
    tmux set-option -g automatic-rename on

    # Check for show-name option
    # The option is enabled if set to any truthy value (non-empty, not "false", not "0")
    local show_name_flag=""
    local show_name
    show_name=$(get_tmux_option "@nerd_icons_show_name" "")
    if [[ -n "${show_name}" && "${show_name}" != "false" && "${show_name}" != "0" ]]; then
        show_name_flag="--show-name"
    fi

    # Build the format command with all required tmux variables
    # These variables are passed to format_output.sh which processes them
    local format_cmd="${CURRENT_DIR}/scripts/format_output.sh"
    format_cmd+=" --process '#{pane_current_command}'"
    format_cmd+=" --title '#{pane_title}'"
    format_cmd+=" --session '#{session_name}'"
    format_cmd+=" --index '#{window_index}'"
    format_cmd+=" --panes '#{window_panes}'"
    format_cmd+=" --active '#{window_active}'"
    format_cmd+=" --pane-pid '#{pane_pid}'"

    if [[ -n "${show_name_flag}" ]]; then
        format_cmd+=" ${show_name_flag}"
    fi

    # Set the automatic-rename-format
    # The #() syntax makes tmux execute the command and use its output
    tmux set-option -g automatic-rename-format "#(${format_cmd})"
}

main "$@"
