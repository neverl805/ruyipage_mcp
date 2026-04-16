# -*- coding: utf-8 -*-
"""js.* tools — JavaScript execution and preload scripts."""

from ..app import mcp
from ..runtime import run_sync, resolve_session, ok, err
from .. import config


@mcp.tool()
async def js_run(
    script: str,
    as_expr: bool = True,
    session_id: str | None = None,
) -> str:
    """Execute JavaScript on the current page and return the result.

    Disabled when RUYIPAGE_MCP_DISABLE_RUN_JS=1.

    Args:
        script: JavaScript code to run.
        as_expr: If True, evaluate as expression and return value.
                 If False, wrap in function body (use 'return ...' for value).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        if not config.allow_run_js():
            return err("js_run is disabled — set RUYIPAGE_MCP_DISABLE_RUN_JS=0 to enable")

        _, entry = resolve_session(session_id)
        result = await run_sync(entry.page.run_js, script, as_expr=as_expr)
        return ok(result)
    except Exception as e:
        return err(e)


@mcp.tool()
async def js_preload(
    op: str,
    script: str | None = None,
    preload_id: str | None = None,
    session_id: str | None = None,
) -> str:
    """Manage preload scripts (injected before every page load).

    Args:
        op: "add" (requires script) or "remove" (requires preload_id).
        script: JavaScript function body to inject (for op="add").
        preload_id: ID of the preload script to remove (for op="remove").
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)

        if op == "add":
            if not script:
                return err("'script' required for op='add'")
            result = await run_sync(entry.page.add_preload_script, script)
            pid = getattr(result, "script_id", None) or str(result)
            return ok({"preload_id": pid})

        elif op == "remove":
            if not preload_id:
                return err("'preload_id' required for op='remove'")
            await run_sync(entry.page.remove_preload_script, preload_id)
            return ok({"removed": preload_id})

        else:
            return err("unknown op '{}' — use add|remove".format(op))
    except Exception as e:
        return err(e)
