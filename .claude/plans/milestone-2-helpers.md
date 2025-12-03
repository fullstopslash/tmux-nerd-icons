# Milestone 2: Shell Helpers

**Target File:** `/home/rain/projects/tmux-nerd-icons/scripts/helpers.sh`

**Dependencies:** None (can be developed in parallel)

## Purpose

Shared shell utilities for reading tmux options, resolving paths, and common operations.

## Requirements

1. POSIX-compatible where possible
2. Bash-specific features clearly marked
3. All functions prefixed to avoid namespace collisions

## Functions

### get_tmux_option

Read a tmux option with fallback default.

```bash
# Usage: get_tmux_option "option_name" "default_value"
# Returns: option value or default
get_tmux_option() {
    local option="$1"
    local default_value="$2"
    local option_value

    option_value=$(tmux show-option -gqv "$option" 2>/dev/null)

    if [ -n "$option_value" ]; then
        echo "$option_value"
    else
        echo "$default_value"
    fi
}
```

### get_config_path

Resolve configuration file path with precedence:
1. `$NERD_ICONS_CONFIG` environment variable
2. `@nerd_icons_config` tmux option
3. `~/.config/nerd-icons/config.yml` (default)

```bash
get_config_path() {
    if [ -n "${NERD_ICONS_CONFIG:-}" ]; then
        echo "$NERD_ICONS_CONFIG"
        return
    fi

    local tmux_config
    tmux_config=$(get_tmux_option "@nerd_icons_config" "")
    if [ -n "$tmux_config" ]; then
        echo "$tmux_config"
        return
    fi

    echo "${HOME}/.config/nerd-icons/config.yml"
}
```

### command_exists

Check if a command is available.

```bash
command_exists() {
    command -v "$1" >/dev/null 2>&1
}
```

### get_python

Find Python 3 interpreter.

```bash
get_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        # Verify it's Python 3
        if python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
            echo "python"
        else
            echo ""
            return 1
        fi
    else
        echo ""
        return 1
    fi
}
```

### log_error

Log errors to stderr with prefix.

```bash
log_error() {
    echo "[nerd-icons] ERROR: $*" >&2
}

log_debug() {
    if [ "${NERD_ICONS_DEBUG:-}" = "1" ]; then
        echo "[nerd-icons] DEBUG: $*" >&2
    fi
}
```

## Complete Implementation

```bash
#!/usr/bin/env bash
# helpers.sh - Shared utilities for tmux-nerd-icons
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# Prevent double-sourcing
if [ -n "${_NERD_ICONS_HELPERS_LOADED:-}" ]; then
    return 0
fi
_NERD_ICONS_HELPERS_LOADED=1

# Get the scripts directory
NERD_ICONS_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NERD_ICONS_PLUGIN_DIR="$(dirname "$NERD_ICONS_SCRIPTS_DIR")"

get_tmux_option() {
    local option="$1"
    local default_value="$2"
    local option_value

    option_value=$(tmux show-option -gqv "$option" 2>/dev/null)

    if [ -n "$option_value" ]; then
        echo "$option_value"
    else
        echo "$default_value"
    fi
}

get_config_path() {
    if [ -n "${NERD_ICONS_CONFIG:-}" ]; then
        echo "$NERD_ICONS_CONFIG"
        return
    fi

    local tmux_config
    tmux_config=$(get_tmux_option "@nerd_icons_config" "")
    if [ -n "$tmux_config" ]; then
        echo "$tmux_config"
        return
    fi

    echo "${HOME}/.config/nerd-icons/config.yml"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        if python -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
            echo "python"
        else
            return 1
        fi
    else
        return 1
    fi
}

log_error() {
    echo "[nerd-icons] ERROR: $*" >&2
}

log_warn() {
    echo "[nerd-icons] WARN: $*" >&2
}

log_debug() {
    if [ "${NERD_ICONS_DEBUG:-}" = "1" ]; then
        echo "[nerd-icons] DEBUG: $*" >&2
    fi
}
```

## Testing

```bash
# Source and test
source scripts/helpers.sh
get_tmux_option "@nonexistent" "default"  # Should output: default
get_config_path  # Should output config path
get_python       # Should output: python3
```

## Linting

```bash
shellcheck scripts/helpers.sh
```
