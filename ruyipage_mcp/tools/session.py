# -*- coding: utf-8 -*-
"""session.* tools — browser lifecycle management."""

from ..app import mcp
from ..registries import sessions
from ..runtime import run_sync, ok, err
from .. import config


@mcp.tool()
async def session_launch(
    port: int = 9222,
    headless: bool = False,
    private: bool = False,
    xpath_picker: bool = False,
    browser_path: str | None = None,
    user_dir: str | None = None,
    window_width: int = 1280,
    window_height: int = 800,
) -> str:
    """Launch a new Firefox browser and return a session_id.

    Uses the custom anti-detection Firefox build by default.

    Args:
        port: Remote debugging port (default 9222).
        headless: Run headless (no visible window).
        private: Enable Firefox private browsing mode.
        xpath_picker: Enable the in-page XPath picker overlay.
        browser_path: Path to firefox.exe (None = use configured default).
        user_dir: Profile / user-data directory (None = temp profile).
        window_width: Initial window width.
        window_height: Initial window height.
    """
    try:
        # Resolve browser path: explicit > env var > built-in default
        effective_path = browser_path or config.default_browser_path()

        # Browser path whitelist check
        whitelist = config.browser_path_whitelist()
        if whitelist and effective_path not in whitelist:
            return err("browser_path '{}' is not in RUYIPAGE_MCP_BROWSER_PATH_WHITELIST".format(
                effective_path))

        from ruyipage import launch as rp_launch

        page = await run_sync(
            rp_launch,
            headless=headless,
            private=private,
            xpath_picker=xpath_picker,
            port=port,
            browser_path=effective_path,
            user_dir=user_dir,
            window_size=(window_width, window_height),
        )
        sid = page.browser.address
        sessions.add(sid, page, owned=True)
        return ok({"session_id": sid, "url": page.url, "title": page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def session_attach(
    address: str = "127.0.0.1:9222",
    tab_index: int = 1,
    latest_tab: bool = False,
) -> str:
    """Attach to an already-running Firefox at *address*.

    Args:
        address: host:port of the remote debugging endpoint.
        tab_index: Which tab to activate (1-based).
        latest_tab: If True, activate the most recently opened tab.
    """
    try:
        from ruyipage import attach_exist_browser

        page = await run_sync(
            attach_exist_browser,
            address=address,
            tab_index=tab_index,
            latest_tab=latest_tab,
        )
        sid = page.browser.address
        sessions.add(sid, page, owned=False)
        return ok({"session_id": sid, "url": page.url, "title": page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def session_auto_attach(
    host: str = "127.0.0.1",
    timeout: float = 0.2,
    latest_tab: bool = True,
) -> str:
    """Auto-detect and attach to a running Firefox / ADS / FlowerBrowser by process signature.

    Args:
        host: Host to scan (default 127.0.0.1).
        timeout: Per-port probe timeout in seconds.
        latest_tab: Activate the most recent tab.
    """
    try:
        from ruyipage import auto_attach_exist_browser_by_process

        page = await run_sync(
            auto_attach_exist_browser_by_process,
            host=host,
            timeout=timeout,
            latest_tab=latest_tab,
        )
        sid = page.browser.address
        sessions.add(sid, page, owned=False)
        return ok({"session_id": sid, "url": page.url, "title": page.title})
    except Exception as e:
        return err(e)


@mcp.tool()
async def session_quit(
    session_id: str | None = None,
    force: bool = False,
) -> str:
    """Close a browser session.

    For sessions created via session_launch (owned=True), this kills the
    browser process.  For attached sessions (owned=False), it only releases
    the local reference — the browser keeps running — unless *force* is True.

    Args:
        session_id: Session to close (auto-resolved if only one exists).
        force: Force-quit even for attached (non-owned) sessions.
    """
    try:
        sid, entry = sessions.resolve(session_id)
        if entry.owned or force:
            await run_sync(entry.page.quit)
        sessions.remove(sid)
        return ok({"closed": sid, "browser_killed": entry.owned or force})
    except Exception as e:
        return err(e)
