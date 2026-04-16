# -*- coding: utf-8 -*-
"""nav.* tools — page navigation."""

from ..app import mcp
from ..runtime import run_sync, resolve_session, ok, err


@mcp.tool()
async def nav_get(
    url: str,
    wait: str = "complete",
    timeout: float | None = None,
    session_id: str | None = None,
) -> str:
    """Navigate to a URL.

    Args:
        url: The URL to open.
        wait: Wait strategy — "complete" (default), "interactive", or "none".
        timeout: Navigation timeout in seconds (None = default).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        kwargs = {"wait": wait}
        if timeout is not None:
            kwargs["timeout"] = timeout
        await run_sync(entry.page.get, url, **kwargs)
        return ok({"url": entry.page.url, "title": entry.page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def nav_back(session_id: str | None = None) -> str:
    """Go back in browser history.

    Args:
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        await run_sync(entry.page.back)
        return ok({"url": entry.page.url, "title": entry.page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def nav_forward(session_id: str | None = None) -> str:
    """Go forward in browser history.

    Args:
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        await run_sync(entry.page.forward)
        return ok({"url": entry.page.url, "title": entry.page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def nav_refresh(session_id: str | None = None) -> str:
    """Refresh the current page.

    Args:
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        await run_sync(entry.page.refresh)
        return ok({"url": entry.page.url, "title": entry.page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def nav_info(session_id: str | None = None) -> str:
    """Return current page URL, title, and ready state.

    Args:
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        p = entry.page
        return ok({
            "url": p.url,
            "title": p.title,
            "ready_state": getattr(p, "ready_state", None),
            "tab_id": getattr(p, "tab_id", None),
        })
    except Exception as e:
        return err(e)
