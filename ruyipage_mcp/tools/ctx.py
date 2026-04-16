# -*- coding: utf-8 -*-
"""ctx.* tools — tabs, emulation, and event subscriptions."""

from ..app import mcp
from ..runtime import run_sync, resolve_session, clamp_timeout, ok, err


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

@mcp.tool()
async def ctx_tabs(
    op: str = "list",
    tab_id: str | None = None,
    url: str | None = None,
    background: bool = False,
    session_id: str | None = None,
) -> str:
    """Manage browser tabs: list, create, close, activate, reload.

    Args:
        op: "list", "create", "close", "activate", or "reload".
        tab_id: Target tab context ID (for close/activate/reload).
        url: Initial URL for a new tab (for create).
        background: Create tab in background (for create).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if op == "list":
            tree = await run_sync(page.contexts.get_tree)
            tabs = []
            for ctx in tree.contexts:
                tabs.append({
                    "context_id": ctx.context,
                    "url": getattr(ctx, "url", ""),
                    "children": len(getattr(ctx, "children", []))
                })
            return ok(tabs)

        elif op == "create":
            new_id = await run_sync(page.contexts.create_tab, url=url, background=background)
            return ok({"tab_id": new_id})

        elif op == "close":
            if not tab_id:
                return err("'tab_id' required for op='close'")
            await run_sync(page.contexts.close, tab_id)
            return ok({"closed": tab_id})

        elif op == "activate":
            if not tab_id:
                return err("'tab_id' required for op='activate'")
            await run_sync(page.contexts.activate, tab_id)
            return ok({"activated": tab_id})

        elif op == "reload":
            await run_sync(page.contexts.reload)
            return ok({"reloaded": True})

        else:
            return err("unknown op '{}' — use list|create|close|activate|reload".format(op))
    except Exception as e:
        return err(e)


# ---------------------------------------------------------------------------
# Emulation
# ---------------------------------------------------------------------------

@mcp.tool()
async def ctx_emulation(
    op: str,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy: float = 100,
    timezone_id: str | None = None,
    locales: str | None = None,
    width: int | None = None,
    height: int | None = None,
    device_pixel_ratio: float | None = None,
    user_agent: str | None = None,
    session_id: str | None = None,
) -> str:
    """Configure device emulation.

    Args:
        op: "set_geolocation", "set_timezone", "set_locale", "apply_mobile_preset",
            "set_offline", or "set_javascript".
        latitude: Geo latitude (for set_geolocation).
        longitude: Geo longitude (for set_geolocation).
        accuracy: Geo accuracy in meters (for set_geolocation, default 100).
        timezone_id: IANA timezone e.g. "Asia/Tokyo" (for set_timezone).
        locales: Comma-separated locale list e.g. "ja-JP,ja" (for set_locale).
        width: Viewport width (for apply_mobile_preset).
        height: Viewport height (for apply_mobile_preset).
        device_pixel_ratio: DPR (for apply_mobile_preset).
        user_agent: Custom UA string (for apply_mobile_preset).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        emu = entry.page.emulation

        if op == "set_geolocation":
            if latitude is None or longitude is None:
                return err("latitude and longitude required")
            await run_sync(emu.set_geolocation, latitude, longitude, accuracy=accuracy)
            return ok({"geolocation": {"lat": latitude, "lon": longitude}})

        elif op == "set_timezone":
            if not timezone_id:
                return err("timezone_id required")
            await run_sync(emu.set_timezone, timezone_id)
            return ok({"timezone": timezone_id})

        elif op == "set_locale":
            if not locales:
                return err("locales required")
            locale_list = [l.strip() for l in locales.split(",")]
            await run_sync(emu.set_locale, locale_list)
            return ok({"locales": locale_list})

        elif op == "apply_mobile_preset":
            kwargs = {}
            if width:
                kwargs["width"] = width
            if height:
                kwargs["height"] = height
            if device_pixel_ratio:
                kwargs["device_pixel_ratio"] = device_pixel_ratio
            if user_agent:
                kwargs["user_agent"] = user_agent
            await run_sync(emu.apply_mobile_preset, **kwargs)
            return ok({"mobile_preset": kwargs})

        elif op == "set_offline":
            await run_sync(emu.set_network_offline, True)
            return ok({"offline": True})

        elif op == "set_javascript":
            enabled = True  # caller can extend
            await run_sync(emu.set_javascript_enabled, enabled)
            return ok({"javascript_enabled": enabled})

        else:
            return err("unknown op '{}' — use set_geolocation|set_timezone|set_locale|apply_mobile_preset".format(op))
    except Exception as e:
        return err(e)


# ---------------------------------------------------------------------------
# Events (navigation / downloads / generic BiDi)
# ---------------------------------------------------------------------------

@mcp.tool()
async def ctx_events(
    op: str,
    kind: str = "events",
    events: str | None = None,
    timeout: float = 10,
    filter_method: str | None = None,
    session_id: str | None = None,
) -> str:
    """Subscribe to and poll BiDi events.

    Unified entry for page.events, page.navigation, and page.downloads.

    Args:
        op: "start", "wait", "stop", or "clear".
        kind: "events" (generic), "navigation", or "downloads".
        events: Comma-separated event names to subscribe to (for start with kind="events").
                e.g. "browsingContext.load,network.beforeRequestSent"
        timeout: Seconds to wait (for wait).
        filter_method: Only return events matching this event name, e.g. "browsingContext.load" (for wait).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if kind == "navigation":
            tracker = page.navigation
        elif kind == "downloads":
            tracker = page.downloads
        else:
            tracker = page.events

        if op == "start":
            if kind == "events" and events:
                ev_list = [e.strip() for e in events.split(",")]
                await run_sync(tracker.start, ev_list)
            else:
                await run_sync(tracker.start)
            return ok({"subscribed": kind})

        elif op == "wait":
            timeout = clamp_timeout(timeout)
            kwargs = {"timeout": timeout}
            if filter_method:
                kwargs["event"] = filter_method
            event = await run_sync(tracker.wait, **kwargs)
            if event is None:
                return ok(None, message="no event within timeout")
            info = {
                "method": getattr(event, "method", ""),
                "context": getattr(event, "context", ""),
                "url": getattr(event, "url", ""),
            }
            for attr in ("status", "request_id", "error_text", "suggested_filename"):
                v = getattr(event, attr, None)
                if v is not None:
                    info[attr] = v
            return ok(info)

        elif op == "stop":
            await run_sync(tracker.stop)
            return ok({"unsubscribed": kind})

        elif op == "clear":
            if hasattr(tracker, "clear"):
                await run_sync(tracker.clear)
            return ok({"cleared": kind})

        else:
            return err("unknown op '{}' — use start|wait|stop|clear".format(op))
    except Exception as e:
        return err(e)
