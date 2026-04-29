# tmux-nerd-icons

Tmux plugin that displays Nerd Font icons in windows based on running process, window title, SSH host, and session name.

## Install

Add to your tmux plugin manager. Scripts: `format_output.sh` (wrapper) and `icon_resolver.py` (engine).

## Configuration

`~/.config/nerd-icons/config.yml` — define icon mappings for processes, sessions, and hosts.

### Activity icons (kitty only)

The nerd-icons config supports `activity-icon` and `activity-icon-color`
fields per app entry, used by the kitty integration to swap glyphs on
unfocused tabs with new output. Tmux **does not** swap the icon glyph on
activity — `automatic-rename` only re-evaluates on PTY output, so the icon
cannot react to tmux's `window_activity_flag` per render. Instead, the
default bubble bar already colours the index digit blue (`colour75`) when
the activity flag is set, which provides the same "this window has unread"
signal without needing a glyph swap. Setting `activity-icon` in the config
is harmless — tmux just ignores it.
