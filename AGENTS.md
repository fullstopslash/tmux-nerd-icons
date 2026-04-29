# Agent Instructions

## Version Management

Versions are bumped automatically. Use the global justfile recipes:

- `just -g bump` — bump patch version (auto-detects project type)
- `just -g bump minor` — bump minor version
- `just -g bump major` — bump major version
- `just -g commit "message"` — auto-bumps patch, then commits via jj

Supported formats: Cargo.toml, pyproject.toml, package.json, setup.py, flake.nix.
Supports semver (X.Y.Z) and datever (YYYY.MM.DD[.N]). Projects without version files are handled silently.
