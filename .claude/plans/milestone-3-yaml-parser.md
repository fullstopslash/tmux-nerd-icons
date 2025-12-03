# Milestone 3: YAML Parser

**Target File:** `/home/rain/projects/tmux-nerd-icons/scripts/yaml_parser.py`

**Dependencies:** None (can be developed in parallel)

## Purpose

Minimal YAML parser for the nerd-icons configuration format. No external dependencies
(no PyYAML, ruamel.yaml, etc.) - pure Python stdlib only.

## Requirements

1. Python 3.10+ (for modern type hints)
2. No external dependencies
3. Parse all config sections: config, icons, title_icons, sessions, hosts, layout-glyps
4. Handle nested structures (icons with title patterns, hosts with colors)
5. Strip inline comments
6. Handle quoted strings
7. File size limit (1MB max for security)
8. Regex pattern length limit (500 chars for ReDoS protection)

## Data Structures

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class IconConfig:
    """Global configuration settings."""
    fallback_icon: str = "󰽙"
    show_name: bool = False
    use_process_name: bool = False
    prefer_host_icon: bool = True
    ring_color_active: str = "#875fff"
    ring_color_inactive: str = "#45475a"
    icon_color: str = "#cdd6f4"
    alert_color: str = "#f38ba8"
    multi_pane_icon: str = ""
    layout_glyphs: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedConfig:
    """Complete parsed configuration."""
    config: IconConfig
    icons: dict[str, str | dict[str, Any]]
    title_icons: dict[str, str]
    sessions: dict[str, str]
    hosts: dict[str, str | dict[str, Any]]
```

## Key Functions

### _strip_yaml_value

```python
def _strip_yaml_value(val: str) -> str:
    """Strip inline comments and surrounding quotes."""
    val = val.strip()
    # Remove inline comments (space + #)
    if " #" in val:
        val = val.split(" #", 1)[0].strip()
    # Remove surrounding quotes
    if val and len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        val = val[1:-1]
    return val
```

### _get_indent_level

```python
def _get_indent_level(line: str) -> int:
    """Get indentation level (number of leading spaces)."""
    return len(line) - len(line.lstrip())
```

### _iter_yaml_block

```python
def _iter_yaml_block(
    lines: list[str],
    block_label: str
) -> Iterator[tuple[str, str | dict[str, Any], int]]:
    """
    Iterate over items in a YAML block.

    Yields: (key, value_or_dict, line_number)

    Handles:
    - Simple values: "key: value"
    - Nested blocks with increased indentation
    """
    # Find block start
    in_block = False
    block_indent = 0
    current_key = None
    current_dict: dict[str, Any] = {}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == f"{block_label}:":
            in_block = True
            block_indent = _get_indent_level(line)
            continue

        if not in_block:
            continue

        indent = _get_indent_level(line)

        # Check if we've left the block
        if indent <= block_indent and ":" in stripped:
            # New top-level block
            if current_key and current_dict:
                yield current_key, current_dict, i
            break

        # Parse key: value
        if ":" in stripped:
            key_part, _, value_part = stripped.partition(":")
            key = _normalize_yaml_key(key_part)
            value = _strip_yaml_value(value_part)

            if indent == block_indent + 2:
                # Top-level item in block
                if current_key and current_dict:
                    yield current_key, current_dict, i
                current_key = key
                current_dict = {}
                if value:
                    # Simple value
                    yield key, value, i
                    current_key = None
            elif indent > block_indent + 2 and current_key:
                # Nested under current key
                current_dict[key] = value

    # Yield final item
    if current_key and current_dict:
        yield current_key, current_dict, len(lines)
```

### load_config

```python
MAX_CONFIG_SIZE = 1024 * 1024  # 1MB

def load_config(path: str) -> ParsedConfig:
    """
    Load and parse the nerd-icons configuration file.

    Args:
        path: Path to config file

    Returns:
        ParsedConfig with all sections parsed

    Raises:
        FileNotFoundError: If config doesn't exist
        ValueError: If config is invalid or too large
    """
    path = os.path.expanduser(path)

    # Security: check file size
    size = os.path.getsize(path)
    if size > MAX_CONFIG_SIZE:
        raise ValueError(f"Config file too large: {size} bytes (max {MAX_CONFIG_SIZE})")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()

    # Parse each section
    config = _parse_config_section(lines)
    icons = dict(_iter_yaml_block(lines, "icons"))
    title_icons = {k: v for k, v, _ in _iter_yaml_block(lines, "title_icons")
                   if isinstance(v, str)}
    sessions = {k: v for k, v, _ in _iter_yaml_block(lines, "sessions")
                if isinstance(v, str)}
    hosts = dict(_iter_yaml_block(lines, "hosts"))
    layout_glyphs = {k: v for k, v, _ in _iter_yaml_block(lines, "layout-glyps")
                     if isinstance(v, str)}

    config.layout_glyphs = layout_glyphs

    return ParsedConfig(
        config=config,
        icons=icons,
        title_icons=title_icons,
        sessions=sessions,
        hosts=hosts,
    )
```

## CLI Interface

```bash
# Validate config
python3 scripts/yaml_parser.py --validate ~/.config/nerd-icons/config.yml

# Dump parsed config as JSON (for debugging)
python3 scripts/yaml_parser.py --dump ~/.config/nerd-icons/config.yml
```

## Reference Implementation

Pattern follows `/home/rain/.config/kitty/tab_bar.py` lines 43-518.

Key patterns to replicate:
- Line-by-line parsing with indentation tracking
- Support for both simple `key: value` and nested blocks
- Inline comment stripping with `" #"` detection
- Quote handling for both single and double quotes

## Testing

```python
def test_simple_icon():
    config = load_config_from_string("""
icons:
  nvim: ""
  zsh: ""
""")
    assert config.icons["nvim"] == ""
    assert config.icons["zsh"] == ""

def test_nested_icon():
    config = load_config_from_string("""
icons:
  firefox:
    icon: ""
    title:
      ".*github.*": ""
""")
    assert config.icons["firefox"]["icon"] == ""
    assert config.icons["firefox"]["title"][".*github.*"] == ""

def test_hosts_with_colors():
    config = load_config_from_string("""
hosts:
  "malphas*":
    icon: ""
    ring-color: "#04a5e5"
""")
    assert config.hosts["malphas*"]["icon"] == ""
    assert config.hosts["malphas*"]["ring-color"] == "#04a5e5"
```

## Linting

```bash
ruff check scripts/yaml_parser.py
ruff format --check scripts/yaml_parser.py
mypy --strict scripts/yaml_parser.py
```
