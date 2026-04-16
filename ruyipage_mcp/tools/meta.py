# -*- coding: utf-8 -*-
"""meta tool — describe capabilities and server state."""

from ..app import mcp
from ..registries import sessions
from ..runtime import ok
from .. import config


@mcp.tool()
async def ruyipage_describe_capabilities() -> str:
    """Return the current server state: active sessions, element counts, capability switches.

    Use this tool when you are unsure what the server can do or need to
    inspect which sessions / elements are active.
    """
    return ok({
        "sessions": sessions.summary(),
        "config": {
            "run_js_enabled": config.allow_run_js(),
            "extensions_enabled": config.allow_extensions(),
            "browser_path_whitelist": config.browser_path_whitelist(),
            "max_elements_per_session": config.max_elements(),
            "event_buffer_size": config.event_buffer_size(),
            "wait_timeout_ceiling_seconds": config.wait_timeout_ceiling(),
        },
        "tool_namespaces": [
            "session  — launch / attach / auto_attach / quit",
            "nav      — get / back / forward / refresh / info",
            "dom      — find / find_all / read / query_in / wait_for / release",
            "act      — click / input / simple / chain",
            "state    — screenshot / save_pdf / cookies / storage",
            "js       — run / preload",
            "net      — intercept / listen / collector / headers / cache",
            "ctx      — tabs / emulation / events",
        ],
    })
