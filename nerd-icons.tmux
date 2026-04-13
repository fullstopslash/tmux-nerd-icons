#!/usr/bin/env bash
# nerd-icons.tmux - TPM entry point for tmux-nerd-icons
#
# Sets window icons via automatic-rename and renders a powerline bubble
# tab bar using native tmux format strings. Zero shell overhead for
# rendering — only the icon resolution uses #() with the nerd-icons binary.
#
# Requires these tmux @options to be set (with PowerLine glyphs):
#   @SEPARATOR_TAB_LEFT    U+E0B6  (endcaps + active bubble left)
#   @SEPARATOR_TAB_RIGHT   U+E0B4  (endcaps + active bubble right)
#   @SEPARATOR_SOFT_LEFT   U+E0B7  (between inactive tabs, points left)
#   @SEPARATOR_SOFT_RIGHT  U+E0B5  (between inactive tabs, points right)
#
# Plugin options (set before loading):
#   @nerd_icons_bubble_bar     "on"|"off"  (default: on)
#   @nerd_icons_act_bg         colour      (default: colour232)
#   @nerd_icons_inact_bg       colour      (default: colour235)
#   @nerd_icons_ring_active    colour      (default: colour99)
#   @nerd_icons_ring_inactive  colour      (default: colour237)
#   @nerd_icons_icon_color     colour      (default: colour39)
#   @nerd_icons_bubble_sep     colour      (default: colour236)
#   @nerd_icons_act_fg         colour      (default: colour252)
#   @nerd_icons_inact_fg       colour      (default: colour245)

set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/helpers.sh
source "${CURRENT_DIR}/scripts/helpers.sh"

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

    # ── Bubble bar ────────────────────────────────────────────
    local bubble_bar
    bubble_bar=$(opt "@nerd_icons_bubble_bar" "on")
    [[ "$bubble_bar" != "on" ]] && return

    local ab ib ra ri ic bs af nf
    ab=$(opt "@nerd_icons_act_bg" "colour232")
    ib=$(opt "@nerd_icons_inact_bg" "colour235")
    ra=$(opt "@nerd_icons_ring_active" "colour99")
    ri=$(opt "@nerd_icons_ring_inactive" "colour237")
    ic=$(opt "@nerd_icons_icon_color" "colour39")
    bs=$(opt "@nerd_icons_bubble_sep" "colour236")
    af=$(opt "@nerd_icons_act_fg" "colour252")
    nf=$(opt "@nerd_icons_inact_fg" "colour245")

    # Separator references (use @options that contain the actual glyphs)
    local TL='#{@SEPARATOR_TAB_LEFT}'   # U+E0B6
    local TR='#{@SEPARATOR_TAB_RIGHT}'  # U+E0B4
    local SL='#{@SEPARATOR_SOFT_LEFT}'  # U+E0B7
    local SR='#{@SEPARATOR_SOFT_RIGHT}' # U+E0B5

    # Ring symbol mapping (window index → nerd font circled number)
    # Uses @RING_* options if set, otherwise falls back to #I
    # Set ring glyphs as tmux options so they survive format storage
    tmux set-option -gq @RING_1  $'\xf3\xb0\xac\xba'
    tmux set-option -gq @RING_2  $'\xf3\xb0\xac\xbb'
    tmux set-option -gq @RING_3  $'\xf3\xb0\xac\xbc'
    tmux set-option -gq @RING_4  $'\xf3\xb0\xac\xbd'
    tmux set-option -gq @RING_5  $'\xf3\xb0\xac\xbe'
    tmux set-option -gq @RING_6  $'\xf3\xb0\xac\xbf'
    tmux set-option -gq @RING_7  $'\xf3\xb0\xad\x80'
    tmux set-option -gq @RING_8  $'\xf3\xb0\xad\x81'
    tmux set-option -gq @RING_9  $'\xf3\xb0\xad\x82'
    tmux set-option -gq @RING_10 $'\xf3\xb0\xbf\xa9'

    local RING='#{?#{==:#I,1},#{@RING_1},#{?#{==:#I,2},#{@RING_2},#{?#{==:#I,3},#{@RING_3},#{?#{==:#I,4},#{@RING_4},#{?#{==:#I,5},#{@RING_5},#{?#{==:#I,6},#{@RING_6},#{?#{==:#I,7},#{@RING_7},#{?#{==:#I,8},#{@RING_8},#{?#{==:#I,9},#{@RING_9},#{?#{==:#I,10},#{@RING_10},#I}}}}}}}}}}'

    # ── Active window format ──────────────────────────────────
    # Left sep: bg=inact if prev, bg=default if first
    # Ring: prefix(13) > zoomed(161) > default
    # Content: RING ICON(#W)
    # Right sep: bg=inact if next, bg=default if last
    local ACTIVE=""
    ACTIVE+="#{?#{window_start_flag},#[fg=${ab}#,bg=default],#[fg=${ab}#,bg=${ib}]}${TL}"
    ACTIVE+="#[bg=${ab}]#{?client_prefix,#[fg=colour13],#{?window_zoomed_flag,#[fg=colour161],#[fg=${ra}]}} ${RING}"
    ACTIVE+="#[fg=${ic}]#W  "
    ACTIVE+="#{?#{window_end_flag},#[fg=${ab}#,bg=default],#[fg=${ab}#,bg=${ib}]}${TR}"

    # ── Inactive window format ────────────────────────────────
    # Before active: left sep + content (no right sep — active handles it)
    # After active: content + right sep (no left sep — active handled it)
    #
    # Left sep (before-active only):
    #   first: endcap TL (fg=ib, bg=default)
    #   not-first: soft SL (fg=bs, bg=ib) — points away from active
    local LEFT_FIRST="#[fg=${ib}#,bg=default]${TL}"
    local LEFT_MID="#[fg=${bs}#,bg=${ib}]${SL}"
    local LEFT="#{?#{e|<:#I,#{active_window_index}},#{?#{window_start_flag},${LEFT_FIRST},${LEFT_MID}},}"

    # Content (all inactive)
    local CONTENT=""
    CONTENT+="#[bg=${ib}]#{?#{window_bell_flag},#[fg=colour196],#{?#{window_activity_flag},#[fg=colour75],#[fg=${ri}]}} ${RING}"
    CONTENT+="#[fg=${ic}]#W"
    CONTENT+="#[fg=${nf}]  "

    # Right sep (after-active only):
    #   last: endcap TR (fg=ib, bg=default)
    #   not-last: soft SR (fg=bs, bg=ib) — points away from active
    local RIGHT_LAST="#[fg=${ib}#,bg=default]${TR}"
    local RIGHT_MID="#[fg=${bs}#,bg=${ib}]${SR}"
    local RIGHT="#{?#{e|>:#I,#{active_window_index}},#{?#{window_end_flag},${RIGHT_LAST},${RIGHT_MID}},}"

    local INACTIVE="${LEFT}${CONTENT}${RIGHT}"

    # ── Apply ─────────────────────────────────────────────────
    tmux set-window-option -g window-status-separator ''
    tmux set-window-option -g window-status-current-format "${ACTIVE}"
    tmux set-window-option -g window-status-format "${INACTIVE}"
}

main "$@"
