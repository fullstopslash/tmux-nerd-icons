#!/usr/bin/env bash
# nerd-icons.tmux - TPM entry point for tmux-nerd-icons
#
# Sets window name to a nerd font icon. Colors and index display
# should be configured in your window-status-format in tmux.conf.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/helpers.sh
source "${CURRENT_DIR}/scripts/helpers.sh"

main() {
    # Build the icon command
    local icon_cmd="${CURRENT_DIR}/scripts/format_output.sh"
    icon_cmd+=" --process '#{pane_current_command}'"
    icon_cmd+=" --title '#{pane_title}'"
    icon_cmd+=" --session '#{session_name}'"
    icon_cmd+=" --panes '#{window_panes}'"
    icon_cmd+=" --pane-pid '#{pane_pid}'"

    # Enable automatic renaming - icon becomes the window name (#W)
    tmux set-option -g automatic-rename on
    tmux set-option -g automatic-rename-format "#(${icon_cmd})"
}

main "$@"
