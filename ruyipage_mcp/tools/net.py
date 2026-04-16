# -*- coding: utf-8 -*-
"""net.* tools — network intercept, listener, data collector, headers, cache."""

import json as _json

from ..app import mcp
from ..runtime import run_sync, resolve_session, clamp_timeout, ok, err


@mcp.tool()
async def net_intercept(
    op: str,
    url_patterns: str | None = None,
    phases: str | None = None,
    timeout: float = 10,
    action: str | None = None,
    session_id: str | None = None,
) -> str:
    """Intercept network requests — start, wait for a request, decide, or stop.

    Workflow:
      1. net_intercept(op="start", url_patterns="api/login")
      2. (trigger navigation / action that fires the request)
      3. net_intercept(op="wait_and_resolve", action='{"mode":"continue"}')
         — or action='{"mode":"mock","status":200,"body":"..."}'
         — or action='{"mode":"fail"}'
      4. net_intercept(op="stop")

    Args:
        op: "start", "wait_and_resolve", "stop", or "list".
        url_patterns: URL substring or pattern (for start).
        phases: Comma-separated phases — "beforeRequestSent", "responseStarted" (for start).
        timeout: Seconds to wait for the intercepted request (for wait_and_resolve).
        action: JSON string with {"mode":"continue|mock|fail", ...} (for wait_and_resolve).
                For mock: {"mode":"mock","status":200,"headers":{},"body":"..."}
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if op == "start":
            kwargs = {}
            if url_patterns:
                patterns = [{"type": "string", "pattern": p.strip()}
                            for p in url_patterns.split(",")]
                kwargs["url_patterns"] = patterns
            if phases:
                phase_list = [p.strip() for p in phases.split(",")]
                kwargs["phases"] = phase_list
            await run_sync(page.intercept.start, **kwargs)
            return ok({"intercepting": True})

        elif op == "wait_and_resolve":
            timeout = clamp_timeout(timeout)
            req = await run_sync(page.intercept.wait, timeout=timeout)
            if req is None:
                return ok(None, message="no intercepted request within timeout")

            # Build request summary
            req_info = {
                "url": getattr(req, "url", ""),
                "method": getattr(req, "method", ""),
                "request_id": getattr(req, "request_id", ""),
            }

            # If no action provided, just return the request info without resolving
            if not action:
                return ok(req_info, message="request intercepted — call again with action to resolve")

            act = _json.loads(action)
            mode = act.get("mode", "continue")
            if mode == "continue":
                await run_sync(req.continue_request,
                               url=act.get("url"),
                               method=act.get("method"),
                               headers=act.get("headers"),
                               body=act.get("body"))
            elif mode == "mock":
                await run_sync(req.mock,
                               status=act.get("status", 200),
                               headers=act.get("headers"),
                               body=act.get("body", ""))
            elif mode == "fail":
                await run_sync(req.fail)
            else:
                return err("unknown action mode '{}'".format(mode))

            req_info["resolved"] = mode
            return ok(req_info)

        elif op == "stop":
            await run_sync(page.intercept.stop)
            return ok({"intercepting": False})

        elif op == "list":
            return ok({"active": True, "message": "use wait_and_resolve to get next pending request"})

        else:
            return err("unknown op '{}' — use start|wait_and_resolve|stop|list".format(op))
    except Exception as e:
        return err(e)


@mcp.tool()
async def net_listen(
    op: str,
    targets: str | None = None,
    method: str | None = None,
    timeout: float = 10,
    count: int = 1,
    session_id: str | None = None,
) -> str:
    """Listen for network requests/responses matching a filter.

    Workflow:
      1. net_listen(op="start", targets="api/data", method="POST")
      2. (trigger action)
      3. net_listen(op="wait", timeout=10)
      4. net_listen(op="stop")

    Args:
        op: "start", "wait", "stop", or "clear".
        targets: URL substring to match (for start).
        method: HTTP method filter e.g. "GET", "POST" (for start).
        timeout: Seconds to wait for matching packets (for wait).
        count: Number of packets to collect before returning (for wait, default 1).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if op == "start":
            kwargs = {}
            if targets:
                kwargs["targets"] = targets
            if method:
                kwargs["method"] = method
            await run_sync(page.listen.start, **kwargs)
            return ok({"listening": True})

        elif op == "wait":
            timeout = clamp_timeout(timeout)
            count = max(1, min(count, 50))
            raw = await run_sync(page.listen.wait, timeout=timeout, count=count)
            # Normalize: count=1 returns single, count>1 returns list
            if not isinstance(raw, list):
                raw = [raw] if raw else []
            packets = []
            for pkt in raw:
                if pkt is None:
                    continue
                info = {
                    "url": getattr(pkt, "url", ""),
                    "method": getattr(pkt, "method", ""),
                    "status": getattr(pkt, "status", None),
                    "request_id": getattr(pkt, "request_id", ""),
                }
                body = getattr(pkt, "body", None)
                if body is not None:
                    if isinstance(body, (bytes, bytearray)):
                        if len(body) <= 512 * 1024:
                            try:
                                info["body"] = body.decode("utf-8", errors="replace")
                            except Exception:
                                info["body"] = "<binary {} bytes>".format(len(body))
                        else:
                            info["body"] = "<truncated {} bytes>".format(len(body))
                    elif isinstance(body, str):
                        if len(body) <= 512 * 1024:
                            info["body"] = body
                        else:
                            info["body"] = body[:512 * 1024] + "...<truncated>"
                    else:
                        info["body"] = str(body)[:2048]
                packets.append(info)
            return ok(packets, count=len(packets))

        elif op == "stop":
            await run_sync(page.listen.stop)
            return ok({"listening": False})

        elif op == "clear":
            await run_sync(page.listen.clear)
            return ok({"cleared": True})

        else:
            return err("unknown op '{}' — use start|wait|stop|clear".format(op))
    except Exception as e:
        return err(e)


@mcp.tool()
async def net_collector(
    op: str,
    events: str | None = None,
    data_types: str | None = None,
    request_id: str | None = None,
    data_type: str = "response",
    session_id: str | None = None,
) -> str:
    """Manage network data collectors (capture request/response bodies).

    Workflow:
      1. net_collector(op="add", events="responseCompleted", data_types="response")
      2. (trigger network activity)
      3. net_collector(op="get", request_id="...", data_type="response")
      4. net_collector(op="remove")

    Args:
        op: "add", "get", or "remove".
        events: Comma-separated collector events — "beforeRequestSent", "responseCompleted" (for add).
        data_types: Comma-separated — "request", "response" (for add).
        request_id: Network request ID to retrieve data for (for get).
        data_type: "request" or "response" (for get, default "response").
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        page = entry.page

        if op == "add":
            ev = [e.strip() for e in (events or "responseCompleted").split(",")]
            dt = [d.strip() for d in (data_types or "response").split(",")]
            collector = await run_sync(page.network.add_data_collector, ev, data_types=dt)
            cid = str(id(collector))
            # Store collector on session entry for later retrieval
            if not hasattr(entry, "_collectors"):
                entry._collectors = {}
            entry._collectors[cid] = collector
            return ok({"collector_id": cid})

        elif op == "get":
            if not request_id:
                return err("'request_id' required for op='get'")
            collectors = getattr(entry, "_collectors", {})
            if not collectors:
                return err("no active collector — call net_collector(op='add') first")
            # Try each collector
            for cid, collector in collectors.items():
                data = await run_sync(collector.get, request_id, data_type=data_type)
                if data is not None:
                    body = str(data)
                    if len(body) > 512 * 1024:
                        body = body[:512 * 1024] + "...<truncated>"
                    return ok({"collector_id": cid, "request_id": request_id, "body": body})
            return ok(None, message="no data found for request_id '{}'".format(request_id))

        elif op == "remove":
            collectors = getattr(entry, "_collectors", {})
            for cid, collector in list(collectors.items()):
                try:
                    await run_sync(collector.remove)
                except Exception:
                    pass
            if hasattr(entry, "_collectors"):
                entry._collectors.clear()
            return ok({"removed": True})

        else:
            return err("unknown op '{}' — use add|get|remove".format(op))
    except Exception as e:
        return err(e)


@mcp.tool()
async def net_headers(
    op: str = "set",
    headers: str | None = None,
    session_id: str | None = None,
) -> str:
    """Set or clear extra request headers.

    Args:
        op: "set" or "clear".
        headers: JSON string of headers dict, e.g. '{"X-Test": "yes"}' (for set).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        if op == "set":
            if not headers:
                return err("'headers' required for op='set'")
            h = _json.loads(headers)
            await run_sync(entry.page.network.set_extra_headers, h)
            return ok({"headers_set": list(h.keys())})
        elif op == "clear":
            await run_sync(entry.page.network.set_extra_headers, {})
            return ok({"headers_cleared": True})
        else:
            return err("unknown op '{}' — use set|clear".format(op))
    except Exception as e:
        return err(e)


@mcp.tool()
async def net_cache(
    behavior: str = "bypass",
    session_id: str | None = None,
) -> str:
    """Set network cache behavior.

    Args:
        behavior: "default" (normal caching) or "bypass" (force re-fetch).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        await run_sync(entry.page.network.set_cache_behavior, behavior)
        return ok({"cache": behavior})
    except Exception as e:
        return err(e)
