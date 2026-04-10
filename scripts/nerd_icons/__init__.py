"""nerd-icons: config-driven icon resolution framework.

Exports:
    resolve_icon: Main resolution function.
    load_config: Load config from file path.
    IconResult: Resolution result dataclass.
    ParsedConfig: Parsed config dataclass.
"""

from .parser import ParsedConfig, load_config
from .resolver import IconResult, resolve_icon

__all__ = ["resolve_icon", "load_config", "IconResult", "ParsedConfig"]
