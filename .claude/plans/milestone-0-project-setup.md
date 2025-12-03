# Milestone 0: Project Setup

**Target Files:**
- `/home/rain/projects/tmux-nerd-icons/pyproject.toml`
- `/home/rain/projects/tmux-nerd-icons/.shellcheckrc`

**Dependencies:** None (do this first)

## Purpose

Set up linting configuration and project metadata before implementing milestones.

## pyproject.toml

```toml
[project]
name = "tmux-nerd-icons"
version = "0.1.0"
description = "Nerd font icons for tmux windows"
readme = "readme.md"
license = "GPL-3.0-only"
requires-python = ">=3.10"
authors = [
    { name = "Your Name" }
]
keywords = ["tmux", "nerd-fonts", "icons", "terminal"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Terminals :: Terminal Emulators/X Terminals",
]

[project.urls]
Repository = "https://github.com/yourusername/tmux-nerd-icons"

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "F",      # pyflakes
    "W",      # pycodestyle warnings
    "I",      # isort
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "RUF",    # ruff-specific
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["yaml_parser", "ssh_parser", "icon_resolver"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
warn_unreachable = true
show_error_codes = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

## .shellcheckrc

```bash
# ShellCheck configuration for tmux-nerd-icons

# Use bash as the default shell
shell=bash

# Allow sourcing files from other locations
external-sources=true

# Enable all optional checks except:
enable=all

# Disable specific checks:
# SC2034: Unused variables (common in sourced helper files)
# SC2155: Declare and assign separately (stylistic choice)
disable=SC2034,SC2155
```

## Directory Structure After Setup

```
tmux-nerd-icons/
├── .claude/
│   └── plans/
│       ├── PLAN.md
│       ├── milestone-0-project-setup.md
│       ├── milestone-1-tpm-entry.md
│       ├── milestone-2-helpers.md
│       ├── milestone-3-yaml-parser.md
│       ├── milestone-4-ssh-parser.md
│       ├── milestone-5-icon-resolver.md
│       └── milestone-6-format-output.md
├── scripts/
│   └── (empty, to be populated)
├── .jj/
├── .git/
├── .shellcheckrc
├── pyproject.toml
├── license.md
├── readme.md
└── todo.md
```

## Linting Commands

After setup, verify linting works:

```bash
# Shell linting
shellcheck --version
shellcheck scripts/*.sh nerd-icons.tmux

# Python linting
ruff check scripts/*.py
ruff format --check scripts/*.py
mypy --strict scripts/*.py
```

## jj Usage

This project uses jj instead of git:

```bash
# Check status
jj status

# Create new change
jj new -m "Add project linting configuration"

# Describe current change
jj describe -m "Implement yaml_parser.py"

# Squash into parent
jj squash

# Update bookmark (like git branch)
jj bookmark set main

# Push (if remote configured)
jj git push
```

## Pre-commit Checks (Optional)

If desired, create a pre-commit script:

```bash
#!/usr/bin/env bash
# .jj/hooks/pre-commit (or use pre-commit framework)

set -e

echo "Running shellcheck..."
shellcheck scripts/*.sh nerd-icons.tmux 2>/dev/null || true

echo "Running ruff..."
ruff check scripts/*.py

echo "Running mypy..."
mypy --strict scripts/*.py

echo "All checks passed!"
```
