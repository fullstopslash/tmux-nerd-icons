#!/usr/bin/env bash
# format_output.sh - Get nerd font icon for tmux window
#
# This file is part of tmux-nerd-icons.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

# shellcheck source=scripts/helpers.sh
source "${SCRIPT_DIR}/helpers.sh"

# Parse command-line arguments
process=""
title=""
session=""
panes=1
pane_pid=""
session_only=0

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
        --panes)
            panes="$2"
            shift 2
            ;;
        --pane-pid)
            pane_pid="$2"
            shift 2
            ;;
        --session-icon)
            # Session-only mode: only resolve session icon, skip process/title/host
            session_only=1
            shift
            ;;
        *)
            # Skip unknown arguments
            shift
            ;;
    esac
done

# get_icon - Get icon from Python resolver
get_icon() {
    local python
    set +e
    python=$(get_python)
    local get_python_result=$?
    set -e

    if [[ ${get_python_result} -ne 0 ]]; then
        echo '{"icon":"󰽙","multi_pane_icon":null}'
        return
    fi

    local config_path
    config_path=$(get_config_path)

    local args=(
        "${SCRIPT_DIR}/icon_resolver.py"
        --config "${config_path}"
    )

    [[ "${session_only}" == "1" ]] && args+=(--session-only)
    [[ -n "${process}" ]] && args+=(--process "${process}")
    [[ -n "${title}" ]] && args+=(--title "${title}")
    [[ -n "${session}" ]] && args+=(--session "${session}")
    [[ -n "${pane_pid}" ]] && args+=(--pane-pid "${pane_pid}")

    "${python}" "${args[@]}" 2>/dev/null || echo '{"icon":"󰽙","multi_pane_icon":null}'
}

# extract_json_field - Extract a field from JSON string
extract_json_field() {
    local json="$1"
    local field="$2"

    local value
    value=$(echo "${json}" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*: *"\([^"]*\)".*/\1/' | head -1)

    echo "${value}"
}

# Main execution
main() {
    local json_result
    json_result=$(get_icon)

    local icon
    icon=$(extract_json_field "${json_result}" "icon")
    [[ -z "${icon}" ]] && icon="󰽙"

    local multi_pane_icon
    multi_pane_icon=$(extract_json_field "${json_result}" "multi_pane_icon")

    # Output just the icon (colors/ring handled by user's window-status-format)
    local output="${icon}"
    if [[ "${panes}" -gt 1 && -n "${multi_pane_icon}" ]]; then
        output="${multi_pane_icon} ${icon}"
    fi

    echo "${output}"
}

main
