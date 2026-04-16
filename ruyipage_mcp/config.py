# -*- coding: utf-8 -*-
"""Environment-variable-based configuration.

All capabilities are ENABLED by default (permissive / self-use mode).
Set the corresponding env var to "1" to disable.
"""

import os


_DEFAULT_BROWSER_PATH = r"E:\ruyi_firefox\firefox.exe"


def _is_disabled(var_name):
    return os.environ.get(var_name, "").strip() == "1"


def default_browser_path():
    """Default Firefox executable path (custom anti-detection build)."""
    return os.environ.get("RUYIPAGE_MCP_BROWSER_PATH", _DEFAULT_BROWSER_PATH)


def allow_run_js():
    return not _is_disabled("RUYIPAGE_MCP_DISABLE_RUN_JS")


def allow_extensions():
    return not _is_disabled("RUYIPAGE_MCP_DISABLE_EXTENSIONS")


def browser_path_whitelist():
    """Return list of allowed browser paths, or None (= any path allowed)."""
    raw = os.environ.get("RUYIPAGE_MCP_BROWSER_PATH_WHITELIST", "").strip()
    if not raw:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def max_elements():
    """Per-session element registry capacity."""
    try:
        return int(os.environ.get("RUYIPAGE_MCP_MAX_ELEMENTS", "512"))
    except ValueError:
        return 512


def event_buffer_size():
    try:
        return int(os.environ.get("RUYIPAGE_MCP_EVENT_BUFFER_SIZE", "500"))
    except ValueError:
        return 500


def wait_timeout_ceiling():
    """Hard ceiling (seconds) for all wait-type tools."""
    try:
        return int(os.environ.get("RUYIPAGE_MCP_WAIT_TIMEOUT_CEILING", "60"))
    except ValueError:
        return 60
