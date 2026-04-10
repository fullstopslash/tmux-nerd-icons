#!/usr/bin/env bash
# format_output.sh - Get nerd font icon for tmux window
#
# This file is part of tmux-nerd-icons.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/helpers.sh
source "${SCRIPT_DIR}/helpers.sh"

FALLBACK_ICON="󰽙"

# Parse command-line arguments
process=""
title=""
session=""
panes=1
pane_pid=""
session_only=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --process|--title|--session|--panes|--pane-pid)
            if [[ $# -lt 2 ]]; then
                log_error "$1 requires a value"
                shift
                break
            fi
            case "$1" in
                --process)  process="$2" ;;
                --title)    title="$2" ;;
                --session)  session="$2" ;;
                --panes)    panes="$2" ;;
                --pane-pid) pane_pid="$2" ;;
            esac
            shift 2
            ;;
        --session-icon)
            session_only=1
            shift
            ;;
        *)
            log_warn "Unknown argument: $1"
            shift
            ;;
    esac
done

# get_icon - Get icon from Python resolver (vendored nerd_icons package)
get_icon() {
    local python
    if ! python=$(get_python); then
        printf '%s\t\n' "${FALLBACK_ICON}"
        return
    fi

    local config_path
    config_path=$(get_config_path) || config_path="${HOME}/.config/nerd-icons/config.yml"

    local args=(
        -m nerd_icons
        --config "${config_path}"
        --tsv
    )

    [[ "${session_only}" == "1" ]] && args+=(--session-only)
    [[ -n "${process}" ]] && args+=(--process "${process}")
    [[ -n "${title}" ]] && args+=(--title "${title}")
    [[ -n "${session}" ]] && args+=(--session "${session}")
    [[ -n "${pane_pid}" ]] && args+=(--pane-pid "${pane_pid}")

    PYTHONPATH="${SCRIPT_DIR}" "${python}" "${args[@]}" 2>/dev/null || printf '%s\t\n' "${FALLBACK_ICON}"
}

# Main execution
main() {
    local result
    result=$(get_icon)

    local icon multi_pane_icon
    IFS=$'\t' read -r icon multi_pane_icon <<< "${result}"
    [[ -z "${icon}" ]] && icon="${FALLBACK_ICON}"

    # Output just the icon (colors/ring handled by user's window-status-format)
    local output="${icon}"
    if [[ "${panes}" =~ ^[0-9]+$ && "${panes}" -gt 1 && -n "${multi_pane_icon}" ]]; then
        output="${multi_pane_icon} ${icon}"
    fi

    printf '%s\n' "${output}"
}

main
