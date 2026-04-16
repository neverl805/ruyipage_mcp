# -*- coding: utf-8 -*-
"""Configuration: JSON config file + environment variable overrides.

Priority (high → low):
  1. Environment variables  (e.g. RUYIPAGE_MCP_BROWSER_PATH)
  2. JSON config file       (ruyipage_mcp.json)
  3. Built-in defaults

Config file search order:
  1. Path given by RUYIPAGE_MCP_CONFIG env var
  2. ./ruyipage_mcp.json  (current working directory)

All capabilities are ENABLED by default (permissive / self-use mode).
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Built-in defaults
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "browser_path": r"E:\ruyi_firefox\firefox.exe",
    "disable_run_js": False,
    "disable_extensions": False,
    "browser_path_whitelist": [],
    "max_elements": 512,
    "event_buffer_size": 500,
    "wait_timeout_ceiling": 60,
}

# ---------------------------------------------------------------------------
# Load config file (once, at import time)
# ---------------------------------------------------------------------------

_file_config: dict = {}


def _find_config_file() -> str | None:
    """Return the first config file path that exists, or None."""
    # 1. Explicit path via env var
    explicit = os.environ.get("RUYIPAGE_MCP_CONFIG", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit

    # 2. Current working directory
    cwd_path = os.path.join(os.getcwd(), "ruyipage_mcp.json")
    if os.path.isfile(cwd_path):
        return cwd_path

    return None


def _load_config_file():
    """Load the JSON config file into ``_file_config``."""
    global _file_config
    path = _find_config_file()
    if path is None:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _file_config = data
            print("[ruyipage-mcp] config loaded from {}".format(path), file=sys.stderr)
    except Exception as exc:
        print("[ruyipage-mcp] WARNING: failed to load config file {}: {}".format(path, exc),
              file=sys.stderr)


_load_config_file()

# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

_ENV_MAP = {
    "browser_path": "RUYIPAGE_MCP_BROWSER_PATH",
    "disable_run_js": "RUYIPAGE_MCP_DISABLE_RUN_JS",
    "disable_extensions": "RUYIPAGE_MCP_DISABLE_EXTENSIONS",
    "browser_path_whitelist": "RUYIPAGE_MCP_BROWSER_PATH_WHITELIST",
    "max_elements": "RUYIPAGE_MCP_MAX_ELEMENTS",
    "event_buffer_size": "RUYIPAGE_MCP_EVENT_BUFFER_SIZE",
    "wait_timeout_ceiling": "RUYIPAGE_MCP_WAIT_TIMEOUT_CEILING",
}


def _get(key: str):
    """Read a config value: env var > config file > default."""
    env_var = _ENV_MAP.get(key)

    # 1. Environment variable
    if env_var:
        raw = os.environ.get(env_var, "").strip()
        if raw:
            return raw

    # 2. Config file
    if key in _file_config:
        return _file_config[key]

    # 3. Built-in default
    return _DEFAULTS[key]


def _get_bool(key: str) -> bool:
    """Read a boolean config value. Env var "1"/"true" → True."""
    val = _get(key)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("1", "true", "yes")
    return bool(val)


def _get_int(key: str) -> int:
    """Read an integer config value."""
    val = _get(key)
    try:
        return int(val)
    except (ValueError, TypeError):
        return _DEFAULTS[key]


# ---------------------------------------------------------------------------
# Public API (unchanged signatures)
# ---------------------------------------------------------------------------

def default_browser_path() -> str:
    """Default Firefox executable path (custom anti-detection build)."""
    return str(_get("browser_path"))


def allow_run_js() -> bool:
    return not _get_bool("disable_run_js")


def allow_extensions() -> bool:
    return not _get_bool("disable_extensions")


def browser_path_whitelist() -> list[str] | None:
    """Return list of allowed browser paths, or None (= any path allowed)."""
    val = _get("browser_path_whitelist")
    # From env var: comma-separated string
    if isinstance(val, str):
        if not val:
            return None
        return [p.strip() for p in val.split(",") if p.strip()]
    # From config file / default: list
    if isinstance(val, list):
        return val if val else None
    return None


def max_elements() -> int:
    """Per-session element registry capacity."""
    return _get_int("max_elements")


def event_buffer_size() -> int:
    return _get_int("event_buffer_size")


def wait_timeout_ceiling() -> int:
    """Hard ceiling (seconds) for all wait-type tools."""
    return _get_int("wait_timeout_ceiling")
