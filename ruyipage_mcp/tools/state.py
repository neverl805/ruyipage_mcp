# -*- coding: utf-8 -*-
"""state.* tools — screenshots, PDF, cookies, storage."""

import json as _json
from mcp.server.fastmcp.utilities.types import Image

from ..app import mcp
from ..runtime import run_sync, resolve_session, resolve_element, ok, err


@mcp.tool()
async def state_screenshot(
    full_page: bool = False,
    element_id: str | None = None,
    save_to: str | None = None,
    session_id: str | None = None,
):
    """Take a screenshot and return it as an image (PNG).

    Args:
        full_page: Capture the full scrollable page (default False).
        element_id: If given, screenshot only this element.
        save_to: Optional file path to save the PNG to disk.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)

        if element_id:
            ee = resolve_element(entry, element_id)
            raw = await run_sync(ee.handle.screenshot, as_bytes=True)
        else:
            raw = await run_sync(entry.page.screenshot, full_page=full_page, as_bytes=True)

        if save_to:
            with open(save_to, "wb") as f:
                f.write(raw)

        return Image(data=raw, format="png")
    except Exception as e:
        return err(e)


@mcp.tool()
async def state_save_pdf(
    path: str,
    session_id: str | None = None,
) -> str:
    """Save the current page as a PDF file.

    Args:
        path: File path to write the PDF.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        await run_sync(entry.page.save_pdf, path)
        return ok({"saved_to": path})
    except Exception as e:
        return err(e)


@mcp.tool()
async def state_cookies(
    op: str = "get",
    name: str | None = None,
    domain: str | None = None,
    cookies: str | None = None,
    session_id: str | None = None,
) -> str:
    """Manage cookies: get, set, or delete.

    Args:
        op: "get" (default), "set", or "delete".
        name: Cookie name filter (for get/delete).
        domain: Cookie domain filter (for get/delete).
        cookies: JSON string of cookie(s) to set — single dict or list of dicts.
                 Each dict: {"name": "...", "value": "...", "domain": "...", "path": "/"}.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if op == "get":
            raw = await run_sync(page.get_cookies, all_info=True)
            result = []
            for c in raw:
                d = {"name": c.name, "value": c.value}
                for attr in ("domain", "path", "http_only", "secure", "same_site", "expiry"):
                    v = getattr(c, attr, None)
                    if v is not None:
                        d[attr] = v
                if name and d["name"] != name:
                    continue
                if domain and d.get("domain", "") != domain:
                    continue
                result.append(d)
            return ok(result)

        elif op == "set":
            if not cookies:
                return err("'cookies' parameter required for op='set'")
            data = _json.loads(cookies)
            await run_sync(page.set_cookies, data)
            count = len(data) if isinstance(data, list) else 1
            return ok({"set_count": count})

        elif op == "delete":
            kwargs = {}
            if name:
                kwargs["name"] = name
            if domain:
                kwargs["domain"] = domain
            await run_sync(page.delete_cookies, **kwargs)
            return ok({"deleted": True, "filter": kwargs or "all"})

        else:
            return err("unknown op '{}' — use get|set|delete".format(op))
    except Exception as e:
        return err(e)


@mcp.tool()
async def state_storage(
    kind: str = "local",
    op: str = "items",
    key: str | None = None,
    value: str | None = None,
    session_id: str | None = None,
) -> str:
    """Read/write localStorage or sessionStorage.

    Args:
        kind: "local" (default) or "session".
        op: "get", "set", "delete", "clear", or "items" (default).
        key: Storage key (for get/set/delete).
        value: Value to store (for set).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        if kind == "local":
            store = entry.page.local_storage
        elif kind == "session":
            store = entry.page.session_storage
        else:
            return err("unknown kind '{}' — use local|session".format(kind))

        if op == "items":
            data = await run_sync(store.items)
            return ok(data)
        elif op == "get":
            if not key:
                return err("'key' required for op='get'")
            val = await run_sync(store.get, key)
            return ok(val)
        elif op == "set":
            if not key:
                return err("'key' required for op='set'")
            await run_sync(store.set, key, value or "")
            return ok({"key": key, "set": True})
        elif op == "delete":
            if not key:
                return err("'key' required for op='delete'")
            await run_sync(store.remove, key)
            return ok({"key": key, "deleted": True})
        elif op == "clear":
            await run_sync(store.clear)
            return ok({"cleared": kind})
        else:
            return err("unknown op '{}' — use items|get|set|delete|clear".format(op))
    except Exception as e:
        return err(e)
