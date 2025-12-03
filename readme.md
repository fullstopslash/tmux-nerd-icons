# tmux-nerd-icons

Nerd Font icons for tmux windows with SSH detection and session-aware icons.

## Features

- **Automatic Window Icons** - Display nerd font icons based on running processes
- **SSH Detection** - Detect SSH/mosh connections and show host-specific icons
- **Session Keywords** - Icons based on tmux session names (code, docker, git, etc.)
- **Title Patterns** - Regex matching for dynamic icons (GitHub in Firefox, etc.)
- **Unified Config** - Uses `~/.config/nerd-icons/config.yml` (shared with Kitty, Waybar)

## Installation

### With TPM (Tmux Plugin Manager)

Add to your `~/.tmux.conf`:

```bash
set -g @plugin 'yourusername/tmux-nerd-icons'
```

Then press `prefix + I` to install.

### Manual

```bash
git clone https://github.com/yourusername/tmux-nerd-icons ~/.tmux/plugins/tmux-nerd-icons
```

Add to `~/.tmux.conf`:

```bash
run-shell ~/.tmux/plugins/tmux-nerd-icons/nerd-icons.tmux
```

## Configuration

The plugin reads from `~/.config/nerd-icons/config.yml`:

```yaml
config:
  fallback-icon: ""
  prefer-host-icon: true
  # multi-pane-icon: "󰎃"  # uncomment to show indicator for multi-pane windows

icons:
  nvim: ""
  zsh: ""
  firefox:
    icon: ""
    title:
      ".*github.*": ""
      "Picture-in-Picture": ""

title_icons:
  ranger: "󰷏"
  btop: ""
  htop: ""

sessions:
  code: "󰨞"
  docker: "󰡨"
  git: "󰊢"

hosts:
  "*.prod.example.com": "󰣇"
  "10.*.*.*": "󰟀"
```

### Tmux Options

| Option | Description | Default |
|--------|-------------|---------|
| `@nerd_icons_config` | Override config path | `~/.config/nerd-icons/config.yml` |

### Styling (Colors, Index, Powerline)

This plugin **only sets the window name** (`#W`) to an icon. All styling should be configured in your own `window-status-format` and `window-status-current-format`.

Example tmux.conf:

```bash
# Active window: cyan icon
set -g window-status-current-format "#[fg=#04a5e5]#I #W#[default]"

# Inactive window: gray icon
set -g window-status-format "#[fg=#666666]#I #W#[default]"
```

## Requirements

- tmux 3.0+
- Python 3.10+
- A [Nerd Font](https://www.nerdfonts.com/) installed and configured in your terminal

## How It Works

1. `nerd-icons.tmux` - TPM entry point, sets up automatic-rename-format
2. `format_output.sh` - Gets icon from resolver, outputs plain icon as window name
3. `icon_resolver.py` - Resolves icon based on process, title, session, host
4. `yaml_parser.py` - Parses config (no external YAML dependencies)
5. `ssh_parser.py` - Detects SSH/mosh connections from command lines

### Icon Resolution Priority

1. Host icon (if SSH detected and `prefer-host-icon: true`)
2. Title patterns (regex in `icons.*.title`)
3. Title icons (TUI apps in `title_icons`)
4. Process name (`icons`)
5. Session keywords (`sessions`)
6. Fallback icon

## License

GPL-3.0 - See [license.md](license.md) for details.
