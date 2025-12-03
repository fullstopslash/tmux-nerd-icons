# tmux-nerd-icons

Nerd Font icons for tmux windows with SSH detection, session-aware icons, and customizable ring symbols.

## Features

- **Automatic Window Icons** - Display nerd font icons based on running processes
- **SSH Detection** - Detect SSH/mosh connections and show host-specific icons
- **Session Keywords** - Icons based on tmux session names (code, docker, git, etc.)
- **Title Patterns** - Regex matching for dynamic icons (GitHub in Firefox, etc.)
- **Ring Symbols** - Rotating window index indicators (󰬺󰬻󰬼󰬽󰬾󰬿󰭀󰭁󰭂󰿩)
- **Active/Inactive Colors** - Visual distinction between focused and background windows
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
  show-name: false
  prefer-host-icon: true
  index-color-active: "#875fff"
  index-color-inactive: "#45475a"

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
  "*.prod.example.com":
    icon: "󰣇"
    ring-color: "#f38ba8"
  "10.*.*.*": "󰟀"
```

### Tmux Options

| Option | Description | Default |
|--------|-------------|---------|
| `@nerd_icons_show_name` | Show window name with icon | `false` |
| `@nerd_icons_config` | Override config path | `~/.config/nerd-icons/config.yml` |

Example:

```bash
set -g @nerd_icons_show_name "true"
```

## Requirements

- tmux 3.0+
- Python 3.10+
- A [Nerd Font](https://www.nerdfonts.com/) installed and configured in your terminal

## How It Works

1. `nerd-icons.tmux` - TPM entry point, sets up automatic-rename-format
2. `format_output.sh` - Generates ring symbol + icon with tmux color codes
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
