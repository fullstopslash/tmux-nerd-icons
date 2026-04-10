"""Config caching with hot reload support.

Caches ParsedConfig in a module-level variable. Checks file mtime on
each call and reloads if changed. Gracefully falls back if the file
is deleted after initial load.
"""

from __future__ import annotations

import os

from .parser import ParsedConfig, load_config

# Module-level cache
_config_cache: ParsedConfig | None = None
_config_mtime: float = 0.0
_config_path_cache: str = ""


def get_config(config_path: str) -> ParsedConfig:
    """Get configuration with caching and hot reload.

    Args:
        config_path: Path to config file (supports ~ expansion).

    Returns:
        Parsed configuration object.

    Raises:
        FileNotFoundError: If config file doesn't exist and no cache available.
    """
    global _config_cache, _config_mtime, _config_path_cache

    path = os.path.expanduser(config_path)

    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        # File missing -- return cache if available, else raise
        if _config_cache is not None:
            return _config_cache
        current_mtime = -1.0

    cache_invalid = (
        _config_cache is None
        or path != _config_path_cache
        or current_mtime != _config_mtime
    )

    if cache_invalid:
        _config_cache = load_config(path)
        _config_mtime = current_mtime
        _config_path_cache = path

    assert _config_cache is not None
    return _config_cache


def clear_cache() -> None:
    """Clear the config cache (useful for testing)."""
    global _config_cache, _config_mtime, _config_path_cache
    _config_cache = None
    _config_mtime = 0.0
    _config_path_cache = ""
