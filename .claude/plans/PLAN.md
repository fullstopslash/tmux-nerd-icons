# tmux-nerd-icons Implementation Plan

A tmux plugin providing nerd-font icons for windows, compatible with the unified
`~/.config/nerd-icons/` configuration standard used by Kitty and Waybar.

## Architecture Overview

```
tmux-nerd-icons/
├── nerd-icons.tmux              # TPM entry point (Milestone 1)
├── scripts/
│   ├── helpers.sh               # Shell helpers (Milestone 2)
│   ├── yaml_parser.py           # Minimal YAML parser (Milestone 3)
│   ├── ssh_parser.py            # SSH/mosh detection (Milestone 4)
│   ├── icon_resolver.py         # Icon resolution engine (Milestone 5)
│   └── format_output.sh         # Ring symbols + formatting (Milestone 6)
├── pyproject.toml               # Python linting config
├── .shellcheckrc                # Shell linting config
└── defaults.yml                 # Fallback defaults
```

## Configuration Standard

The plugin reads from `~/.config/nerd-icons/config.yml`:

```yaml
config:
  fallback-icon: ""
  show-name: false
  use-process-name: false
  prefer-host-icon: true
  index-color-active: "#875fff"
  index-color-inactive: "#45475a"
  alert-color: "#ff0000"

layout-glyps:
  tall: ""
  stack: ""

icons:
  nvim:
    icon: ""
    title:
      ".*github.*": ""
  zsh: ""
  firefox: ""

title_icons:
  ranger: "󰷏"
  btop: ""

sessions:
  code: "󰨞"
  browser: "󰖟"

hosts:
  "malphas*":
    icon: ""
    ring-color: "#04a5e5"
  "10.*.*.*": "󰟀"
```

## Milestone Summary

| Milestone | File | Language | Description |
|-----------|------|----------|-------------|
| 1 | `nerd-icons.tmux` | Bash | TPM entry point |
| 2 | `scripts/helpers.sh` | Bash | Shell utilities |
| 3 | `scripts/yaml_parser.py` | Python | YAML parser (no deps) |
| 4 | `scripts/ssh_parser.py` | Python | SSH host detection |
| 5 | `scripts/icon_resolver.py` | Python | Icon matching |
| 6 | `scripts/format_output.sh` | Bash | Output formatting |

## Dependency Graph

```
nerd-icons.tmux
    ├── sources → scripts/helpers.sh
    └── calls   → scripts/format_output.sh
                      └── calls → scripts/icon_resolver.py
                                      ├── imports → scripts/yaml_parser.py
                                      └── calls   → scripts/ssh_parser.py
```

## Development Order

**Phase 1 (Parallel):** Milestones 2, 3, 4 have no interdependencies
**Phase 2 (Sequential):** Milestone 5 depends on 3, 4
**Phase 3 (Sequential):** Milestone 6 depends on 5
**Phase 4 (Sequential):** Milestone 1 depends on 2, 6

## Linting Requirements

- Shell: `shellcheck --severity=warning`
- Python: `ruff check && ruff format --check && mypy --strict`

## Version Control

Use `jj` (not git) for all operations:
```bash
jj new -m "description"
jj describe -m "updated message"
jj squash
```

## Reference Implementations

- Kitty tab_bar.py: `/home/rain/.config/kitty/tab_bar.py`
- Waybar get_nerd_icon.py: `/home/rain/.config/waybar/scripts/get_nerd_icon.py`
- Config files: `/home/rain/.config/nerd-icons/`
