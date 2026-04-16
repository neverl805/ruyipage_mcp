# -*- coding: utf-8 -*-
"""act.* tools — element interaction and action chains.

All interactions default to native BiDi (isTrusted=true).

Key design choice: we use ``ele.click.left()`` instead of ``ele.click_self()``
because ``click.left()`` uses ``_get_center()`` which checks element
``width/height`` for validity, while ``click_self()`` rejects any element
whose center happens to be at coordinate ``(0, 0)`` — a false negative
that breaks elements near the top-left of the viewport (e.g. Baidu's
search box after a scroll).

For input, ``ele.input(clear=True)`` internally calls ``click_self()``
inside ``clear()``.  We bypass that by doing native focus + Ctrl+A+Delete
via ``click.left()`` + actions chain, then ``ele.input(text, clear=False)``
for the pure BiDi keyboard typing.
"""

from ..app import mcp
from ..runtime import (
    run_sync, resolve_session, resolve_element_or_locator, ok, err,
)


def _native_click(ele, page, times=1):
    """Native isTrusted click via Clicker (uses _get_center, not click_self)."""
    ele.click.left(times=times)


def _native_right_click(ele, page):
    """Native isTrusted right-click via Clicker."""
    ele.click.right()


def _native_focus_and_clear(ele, page):
    """Native isTrusted focus + clear: click.left for focus, then Ctrl+A+Delete via actions."""
    from ruyipage import Keys
    ele.click.left()
    page.actions.combo(Keys.CONTROL, "a").perform()
    page.actions.press(Keys.DELETE).perform()


@mcp.tool()
async def act_click(
    target: str,
    button: str = "left",
    by_js: bool = False,
    session_id: str | None = None,
) -> str:
    """Click an element using native BiDi actions (isTrusted=true).

    Args:
        target: An element_id (el_...) or a locator string (css:/xpath:/text:/#id).
        button: "left" (default), "right", or "double".
        by_js: Force JavaScript click (loses isTrusted -- avoid unless necessary).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        ele, eid = await run_sync(resolve_element_or_locator, entry, target)
        page = entry.page

        if by_js:
            await run_sync(ele.click_self, by_js=True)
            return ok({"clicked": eid or target, "button": button, "mode": "js"})

        if button == "right":
            await run_sync(_native_right_click, ele, page)
        elif button == "double":
            await run_sync(_native_click, ele, page, times=2)
        else:
            await run_sync(_native_click, ele, page)

        return ok({"clicked": eid or target, "button": button, "mode": "native"})
    except Exception as e:
        return err(e)


@mcp.tool()
async def act_input(
    target: str,
    text: str,
    clear: bool = True,
    by_js: bool = False,
    session_id: str | None = None,
) -> str:
    """Type text into an input element using native BiDi keyboard actions (isTrusted=true).

    Automatically falls back to JS input if native BiDi input fails due
    to the element being outside the viewport.

    Args:
        target: An element_id (el_...) or a locator string.
        text: Text to type.
        clear: Clear existing content first (default True).
        by_js: Force JS-based input (loses isTrusted -- avoid unless necessary).
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        ele, eid = await run_sync(resolve_element_or_locator, entry, target)
        page = entry.page

        if by_js:
            await run_sync(ele.input, text, clear=clear, by_js=True)
            return ok({"input_to": eid or target, "text_length": len(text), "mode": "js"})

        # Native path: focus via click.left() + clear via actions + type via BiDi keyboard
        if clear:
            await run_sync(_native_focus_and_clear, ele, page)
            # Type with clear=False since we already cleared
            await run_sync(ele.input, text, clear=False, by_js=False)
        else:
            await run_sync(ele.input, text, clear=False, by_js=False)

        return ok({"input_to": eid or target, "text_length": len(text), "mode": "native"})
    except Exception as e:
        return err(e)


@mcp.tool()
async def act_simple(
    target: str,
    op: str = "hover",
    session_id: str | None = None,
) -> str:
    """Perform a simple action on an element.

    Args:
        target: An element_id (el_...) or a locator string.
        op: One of "hover", "clear", "focus", "scroll_into_view".
        session_id: Session (auto-resolved if only one exists).
    """
    try:
        _, entry = resolve_session(session_id)
        ele, eid = await run_sync(resolve_element_or_locator, entry, target)
        page = entry.page

        if op == "hover":
            await run_sync(ele.hover)
        elif op == "clear":
            await run_sync(_native_focus_and_clear, ele, page)
        elif op == "focus":
            await run_sync(_native_click, ele, page)
        elif op == "scroll_into_view":
            await run_sync(lambda: ele.scroll.to_see())
        else:
            return err("unknown op '{}' — use hover|clear|focus|scroll_into_view".format(op))
        return ok({"op": op, "target": eid or target})
    except Exception as e:
        return err(e)


@mcp.tool()
async def act_chain(
    steps: str,
    session_id: str | None = None,
) -> str:
    """Execute a sequence of input actions as a single BiDi perform call.

    *steps* is a JSON array of action objects. Each object has an "action"
    key and optional parameters.

    Supported actions:
      {"action": "press", "key": "Enter"}
      {"action": "click"}
      {"action": "click", "element_id": "el_abc123"}
      {"action": "move_to", "element_id": "el_abc123"}
      {"action": "move_to", "x": 100, "y": 200}
      {"action": "double_click"}
      {"action": "right_click"}
      {"action": "key_down", "key": "Shift"}
      {"action": "key_up", "key": "Shift"}
      {"action": "type", "text": "hello"}
      {"action": "scroll", "x": 0, "y": -300}
      {"action": "pause", "duration": 500}

    Args:
        steps: JSON array string of action steps.
        session_id: Session (auto-resolved if only one exists).
    """
    import json as _json

    try:
        _, entry = resolve_session(session_id)
        step_list = _json.loads(steps)
        if not isinstance(step_list, list):
            return err("steps must be a JSON array")

        page = entry.page
        from ruyipage import Keys

        def _build_and_perform():
            chain = page.actions
            for step in step_list:
                action = step.get("action", "")

                if action == "press":
                    key = step.get("key", "")
                    key_val = getattr(Keys, key.upper(), key) if key else key
                    chain = chain.press(key_val)

                elif action == "click":
                    eid = step.get("element_id")
                    if eid:
                        ee = entry.elements.get(eid)
                        if ee:
                            chain = chain.move_to(ee.handle).click()
                        else:
                            chain = chain.click()
                    else:
                        chain = chain.click()

                elif action == "double_click":
                    chain = chain.double_click()

                elif action == "right_click":
                    chain = chain.right_click()

                elif action == "move_to":
                    eid = step.get("element_id")
                    if eid:
                        ee = entry.elements.get(eid)
                        if ee:
                            chain = chain.move_to(ee.handle)
                    else:
                        x = step.get("x", 0)
                        y = step.get("y", 0)
                        chain = chain.move_to((x, y))

                elif action == "key_down":
                    key = step.get("key", "")
                    key_val = getattr(Keys, key.upper(), key) if key else key
                    chain = chain.key_down(key_val)

                elif action == "key_up":
                    key = step.get("key", "")
                    key_val = getattr(Keys, key.upper(), key) if key else key
                    chain = chain.key_up(key_val)

                elif action == "type":
                    text = step.get("text", "")
                    for ch in text:
                        chain = chain.press(ch)

                elif action == "scroll":
                    x = step.get("x", 0)
                    y = step.get("y", -300)
                    chain = chain.scroll(x, y)

                elif action == "pause":
                    duration = step.get("duration", 100)
                    chain = chain.pause(duration)

            chain.perform()

        await run_sync(_build_and_perform)
        return ok({"steps_executed": len(step_list)})
    except Exception as e:
        return err(e)
