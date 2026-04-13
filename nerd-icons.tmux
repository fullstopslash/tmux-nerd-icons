#!/usr/bin/env bash
# nerd-icons.tmux - TPM entry point for tmux-nerd-icons
#
# Sets window icons via automatic-rename and optionally renders a
# powerline bubble tab bar using native tmux format strings.
#
# Options (set before loading plugin):
#   @nerd_icons_bubble_bar  "on"|"off"  Enable bubble bar (default: on)
#   @nerd_icons_act_bg      colour      Active tab bg (default: colour232)
#   @nerd_icons_inact_bg    colour      Inactive tab bg (default: colour235)
#   @nerd_icons_ring_active colour      Ring color active (default: colour99)
#   @nerd_icons_ring_inactive colour    Ring color inactive (default: colour237)
#   @nerd_icons_icon_color  colour      Icon color (default: colour39)
#   @nerd_icons_bubble_sep  colour      Soft separator color (default: colour236)
#   @nerd_icons_act_fg      colour      Active tab fg (default: colour252)
#   @nerd_icons_inact_fg    colour      Inactive tab fg (default: colour245)

set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/helpers.sh
source "${CURRENT_DIR}/scripts/helpers.sh"

# Read a tmux option with default
opt() {
    local val
    val=$(tmux show-option -gqv "$1" 2>/dev/null) || true
    printf '%s' "${val:-$2}"
}

main() {
    # ── Icon resolution via automatic-rename ──────────────────
    local icon_cmd="${CURRENT_DIR}/scripts/format_output.sh"
    icon_cmd+=" --process '#{pane_current_command}'"
    icon_cmd+=" --title '#{pane_title}'"
    icon_cmd+=" --session '#{session_name}'"
    icon_cmd+=" --panes '#{window_panes}'"
    icon_cmd+=" --pane-pid '#{pane_pid}'"

    tmux set-option -g automatic-rename on
    tmux set-option -g automatic-rename-format "#(${icon_cmd})"

    # ── Bubble bar (native format strings) ────────────────────
    local bubble_bar
    bubble_bar=$(opt "@nerd_icons_bubble_bar" "on")
    [[ "$bubble_bar" != "on" ]] && return

    # Read colors from tmux options
    local act_bg inact_bg ring_act ring_inact icon_color bubble_sep act_fg inact_fg
    act_bg=$(opt "@nerd_icons_act_bg" "colour232")
    inact_bg=$(opt "@nerd_icons_inact_bg" "colour235")
    ring_act=$(opt "@nerd_icons_ring_active" "colour99")
    ring_inact=$(opt "@nerd_icons_ring_inactive" "colour237")
    icon_color=$(opt "@nerd_icons_icon_color" "colour39")
    bubble_sep=$(opt "@nerd_icons_bubble_sep" "colour236")
    act_fg=$(opt "@nerd_icons_act_fg" "colour252")
    inact_fg=$(opt "@nerd_icons_inact_fg" "colour245")

    # Separator glyphs (hex-escaped to survive editors)
    local sep_l sep_r
    sep_l=$'\xee\x82\xb6'  # U+E0B6  left half-circle
    sep_r=$'\xee\x82\xb4'  # U+E0B4  right half-circle

    # Ring symbol index mapping (nerd font circled numbers 1-10)
    local ring
    ring="#{?#{==:#I,1},$'\xf3\xb0\xac\xba'"
    ring+=",#{?#{==:#I,2},$'\xf3\xb0\xac\xbb'"
    ring+=",#{?#{==:#I,3},$'\xf3\xb0\xac\xbc'"
    ring+=",#{?#{==:#I,4},$'\xf3\xb0\xac\xbd'"
    ring+=",#{?#{==:#I,5},$'\xf3\xb0\xac\xbe'"
    ring+=",#{?#{==:#I,6},$'\xf3\xb0\xac\xbf'"
    ring+=",#{?#{==:#I,7},$'\xf3\xb0\xad\x80'"
    ring+=",#{?#{==:#I,8},$'\xf3\xb0\xad\x81'"
    ring+=",#{?#{==:#I,9},$'\xf3\xb0\xad\x82'"
    ring+=",#{?#{==:#I,10},$'\xf3\xb0\xbf\xa9'"
    ring+=",#I}}}}}}}}}}"

    # ── Active window format ──────────────────────────────────
    # Structure: SEP_L SPACE RING ICON SPACE SPACE SEP_R
    # Left sep bg: inact_bg if prev exists, default if first
    # Right sep bg: inact_bg if next exists, default if last
    # Ring color: prefix(13) > zoomed(161) > bell(196) > default
    local active_fmt=""
    active_fmt+="#{?#{window_start_flag},#[fg=${act_bg},bg=default],#[fg=${act_bg},bg=${inact_bg}]}${sep_l}"
    active_fmt+="#[bg=${act_bg}]#{?client_prefix,#[fg=colour13],#{?window_zoomed_flag,#[fg=colour161],#[fg=${ring_act}]}} ${ring}"
    active_fmt+="#[fg=${icon_color}]#W  "
    active_fmt+="#{?#{window_end_flag},#[fg=${act_bg},bg=default],#[fg=${act_bg},bg=${inact_bg}]}${sep_r}"

    # ── Inactive window format ────────────────────────────────
    # Before active: left sep (endcap if first, bubble if not-first) + content + no right sep
    # After active: no left sep + content + right sep (endcap if last, bubble if not-last)
    #
    # Left separator (before-active only):
    #   first → endcap: fg=inact_bg, bg=default, SEP_L
    #   not-first → bubble: fg=bubble_sep, bg=inact_bg, SEP_L (pointing away from active)
    local left_sep="#{?#{e|<:#I,#{active_window_index}},#{?#{window_start_flag},#[fg=${inact_bg},bg=default]${sep_l},#[fg=${bubble_sep},bg=${inact_bg}]${sep_l}},}"

    # Content: ring(bell>activity>default) + icon(#W)
    local content="#[bg=${inact_bg}]#{?#{window_bell_flag},#[fg=colour196],#{?#{window_activity_flag},#[fg=colour75],#[fg=${ring_inact}]}} ${ring}#[fg=${icon_color}]#W#[fg=${inact_fg}]  "

    # Right separator (after-active only):
    #   last → endcap: fg=inact_bg, bg=default, SEP_R
    #   not-last → bubble: fg=bubble_sep, bg=inact_bg, SEP_R (pointing away from active)
    local right_sep="#{?#{e|>:#I,#{active_window_index}},#{?#{window_end_flag},#[fg=${inact_bg},bg=default]${sep_r},#[fg=${bubble_sep},bg=${inact_bg}]${sep_r}},}"

    local inactive_fmt="${left_sep}${content}${right_sep}"

    # ── Apply ─────────────────────────────────────────────────
    tmux set-window-option -g window-status-separator ''
    tmux set-window-option -g window-status-current-format "$active_fmt"
    tmux set-window-option -g window-status-format "$inactive_fmt"
}

main "$@"
