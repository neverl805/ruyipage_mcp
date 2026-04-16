# -*- coding: utf-8 -*-
"""dom.* tools — element finding and reading."""

from ..app import mcp
from ..runtime import (
    run_sync, resolve_session, resolve_element,
    element_preview, ok, err,
)


@mcp.tool()
async def dom_find(
    locator: str,
    timeout: float | None = None,
    session_id: str | None = None,
) -> str:
    """Find a single element on the page.

    Locator formats: "#id", "css:div.cls", "xpath://button", "text:Login", "tag:input".
    Returns an element_id you can pass to other tools.

    Args:
        locator: CSS / XPath / text / tag locator string.
        timeout: Search timeout in seconds.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        ele = await run_sync(entry.page.ele, locator, **kwargs)
        if not ele or getattr(ele, "_type", "") == "NoneElement":
            return ok(None, found=False, message="no element matched '{}'".format(locator))
        eid = entry.elements.add(ele, locator_hint=locator)
        preview = element_preview(ele)
        return ok({"element_id": eid, **preview}, found=True)
    except Exception as e:
        return err(e)


@mcp.tool()
async def dom_find_all(
    locator: str,
    limit: int = 20,
    timeout: float | None = None,
    session_id: str | None = None,
) -> str:
    """Find all matching elements on the page.

    Args:
        locator: CSS / XPath / text / tag locator string.
        limit: Max elements to return (default 20, cap 100).
        timeout: Search timeout in seconds.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        limit = min(max(int(limit), 1), 100)
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        elements = await run_sync(entry.page.eles, locator, **kwargs)
        results = []
        for ele in elements[:limit]:
            if not ele or getattr(ele, "_type", "") == "NoneElement":
                continue
            eid = entry.elements.add(ele, locator_hint=locator)
            preview = element_preview(ele)
            results.append({"element_id": eid, **preview})
        return ok(results, total_found=len(elements), returned=len(results))
    except Exception as e:
        return err(e)


@mcp.tool()
async def dom_read(
    element_id: str,
    what: str = "text",
    session_id: str | None = None,
) -> str:
    """Read a property from a previously found element.

    Args:
        element_id: Element handle returned by dom_find / dom_find_all.
        what: One of "text", "html", "inner_html", "outer_html", "value", "attrs", "rect", "all".
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        ee = resolve_element(entry, element_id)
        ele = ee.handle

        if what == "text":
            return ok(await run_sync(lambda: ele.text))
        elif what == "html" or what == "outer_html":
            return ok(await run_sync(lambda: ele.html))
        elif what == "inner_html":
            return ok(await run_sync(lambda: ele.inner_html if hasattr(ele, 'inner_html') else ele.html))
        elif what == "value":
            return ok(await run_sync(lambda: ele.value))
        elif what == "attrs":
            preview = element_preview(ele)
            return ok(preview["attrs"])
        elif what == "rect":
            try:
                r = await run_sync(lambda: ele.rect)
                return ok(r)
            except Exception:
                return ok(None, message="rect not available")
        elif what == "all":
            data = {
                "text": await run_sync(lambda: ele.text),
                "value": await run_sync(lambda: ele.value),
                "tag": await run_sync(lambda: ele.tag) if hasattr(ele, "tag") else None,
            }
            data["attrs"] = element_preview(ele)["attrs"]
            return ok(data)
        else:
            return err("unknown 'what' value: '{}' — use text|html|inner_html|outer_html|value|attrs|rect|all".format(what))
    except Exception as e:
        return err(e)


@mcp.tool()
async def dom_query_in(
    element_id: str,
    locator: str,
    session_id: str | None = None,
) -> str:
    """Find a child element inside a previously found element.

    Args:
        element_id: Parent element handle.
        locator: CSS / XPath / text / tag locator string.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        parent_entry = resolve_element(entry, element_id)
        child = await run_sync(parent_entry.handle.ele, locator)
        if not child or getattr(child, "_type", "") == "NoneElement":
            return ok(None, found=False, message="no child matched '{}'".format(locator))
        eid = entry.elements.add(child, locator_hint=locator)
        preview = element_preview(child)
        return ok({"element_id": eid, **preview}, found=True)
    except Exception as e:
        return err(e)


@mcp.tool()
async def dom_wait_for(
    locator: str,
    timeout: float = 10,
    session_id: str | None = None,
) -> str:
    """Wait for an element to appear on the page.

    Args:
        locator: CSS / XPath / text / tag locator string.
        timeout: Max seconds to wait.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        ele = await run_sync(entry.page.ele, locator, timeout=timeout)
        if not ele or getattr(ele, "_type", "") == "NoneElement":
            return ok(None, found=False, message="timed out waiting for '{}'".format(locator))
        eid = entry.elements.add(ele, locator_hint=locator)
        preview = element_preview(ele)
        return ok({"element_id": eid, **preview}, found=True)
    except Exception as e:
        return err(e)


@mcp.tool()
async def dom_release(
    element_id: str,
    session_id: str | None = None,
) -> str:
    """Release an element handle from the registry.

    Args:
        element_id: Element handle to release.
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        removed = entry.elements.remove(element_id)
        return ok({"released": element_id, "was_present": removed is not None})
    except Exception as e:
        return err(e)
