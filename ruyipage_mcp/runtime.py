# -*- coding: utf-8 -*-
"""Async-to-sync bridge and shared helpers.

ruyipage is entirely synchronous (threads + Queue).  MCP FastMCP is asyncio.
Every ruyipage call from a tool handler goes through ``run_sync`` so the
event loop stays unblocked.
"""

import asyncio
import functools
import json

from .registries import sessions, ElementEntry
from . import config


async def run_sync(func, *args, **kwargs):
    """Run *func* in a thread so we don't block the MCP event loop."""
    return await asyncio.to_thread(functools.partial(func, *args, **kwargs))


def resolve_session(session_id=None):
    """Return (session_id, SessionEntry).  Raises ValueError on failure."""
    return sessions.resolve(session_id)


def resolve_element(session_entry, element_id):
    """Return the ElementEntry for *element_id*, with stale auto-recovery.

    If the remote handle is dead but a ``locator_hint`` exists, re-query once.
    Raises ValueError if unrecoverable.
    """
    entry = session_entry.elements.get(element_id)
    if entry is None:
        raise ValueError("element '{}' not found in registry".format(element_id))

    # Stale check — try a cheap attribute access
    try:
        _ = entry.handle.tag
        return entry
    except Exception:
        pass

    # Attempt auto-recovery via locator
    if entry.locator_hint:
        try:
            new_handle = session_entry.page.ele(entry.locator_hint)
            if new_handle and getattr(new_handle, "_type", "") != "NoneElement":
                entry.handle = new_handle
                entry.touch()
                return entry
        except Exception:
            pass

    session_entry.elements.remove(element_id)
    raise ValueError(
        "element '{}' is stale and could not be recovered — re-query with dom_find".format(
            element_id))


def resolve_element_or_locator(session_entry, ref):
    """Accept either an element_id (``el_…``) or a CSS/XPath locator string.

    Returns (FirefoxElement, element_id_or_None).
    """
    if ref.startswith("el_"):
        entry = resolve_element(session_entry, ref)
        return entry.handle, ref

    # It's a locator — find and register
    ele = session_entry.page.ele(ref)
    if not ele or getattr(ele, "_type", "") == "NoneElement":
        raise ValueError("no element found for locator '{}'".format(ref))
    eid = session_entry.elements.add(ele, locator_hint=ref)
    return ele, eid


def element_preview(ele):
    """Build a short preview dict for a found element."""
    try:
        tag = ele.tag if hasattr(ele, "tag") else ""
    except Exception:
        tag = "?"
    try:
        text = (ele.text or "")[:120]
    except Exception:
        text = ""
    try:
        attrs = {}
        for a in ("id", "class", "name", "href", "src", "type", "value", "placeholder"):
            v = ele.attr(a)
            if v:
                attrs[a] = v[:80]
    except Exception:
        attrs = {}
    return {"tag": tag, "text_preview": text, "attrs": attrs}


def ok(data=None, **extra):
    """Standard success envelope."""
    result = {"ok": True}
    if data is not None:
        result["data"] = data
    result.update(extra)
    return json.dumps(result, ensure_ascii=False, default=str)


def err(message):
    """Standard error envelope."""
    return json.dumps({"ok": False, "error": str(message)}, ensure_ascii=False)


def clamp_timeout(timeout):
    """Enforce hard ceiling on wait-style timeouts."""
    ceiling = config.wait_timeout_ceiling()
    if timeout is None:
        return ceiling
    return min(max(float(timeout), 0.1), ceiling)
