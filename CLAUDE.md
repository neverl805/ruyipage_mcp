# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ruyipage-mcp is a standalone MCP (Model Context Protocol) server that exposes browser automation capabilities via the ruyiPage Firefox BiDi library. It runs on stdio transport (JSON-RPC 2.0) and is designed to be used with Claude Code or other MCP clients.

## Commands

```bash
# Install (editable)
pip install -e .

# Run the MCP server (stdio transport)
python -m ruyipage_mcp

# Register with Claude Code
claude mcp add --scope user ruyipage python -- -m ruyipage_mcp
```

There are no tests, linters, or CI configured yet.

## Architecture

### Entry Point Chain

`python -m ruyipage_mcp` → `__main__.py` → `server.run()` → imports all tool modules (triggering `@mcp.tool()` registration) → `mcp.run(transport="stdio")`

### Core Modules

- **`app.py`** — Creates the single global `FastMCP("ruyipage-mcp")` instance imported by all tool modules.
- **`config.py`** — Environment-variable-based configuration. All capabilities are enabled by default (permissive mode).
- **`registries.py`** — `SessionRegistry` (keyed by `host:port`) and per-session `ElementRegistry` (LRU-bounded `OrderedDict`, default cap 512). Element IDs are `el_` + 6 hex chars.
- **`runtime.py`** — Async/sync bridge (`run_sync` wraps synchronous ruyiPage calls via `asyncio.to_thread`). Also provides `ok()`/`err()` response envelope helpers and `resolve_session`/`resolve_element` lookup functions.
- **`server.py`** — Imports all tool modules with `# noqa: F401` to trigger decorator registration. Registers atexit cleanup for owned sessions.

### Tool Modules (`tools/`)

34 tools across 9 modules, organized by namespace prefix:

| Module | Prefix | Purpose |
|---|---|---|
| `session.py` | `session_` | Launch, attach, auto-attach, quit browser sessions |
| `nav.py` | `nav_` | Navigation: goto URL, back, forward, refresh, page info |
| `dom.py` | `dom_` | Find elements, read properties, wait for elements |
| `act.py` | `act_` | Click, input, hover, action chains (BiDi actions API) |
| `state.py` | `state_` | Screenshots, PDF export, cookies, storage |
| `js.py` | `js_` | Execute JS, manage preload scripts |
| `net.py` | `net_` | Network interception, listeners, collectors, headers, cache |
| `ctx.py` | `ctx_` | Tab management, device emulation, BiDi event subscriptions |
| `meta.py` | — | `ruyipage_describe_capabilities` introspection tool |

### Key Patterns

- **All tool functions are async**, decorated with `@mcp.tool()`. Docstrings become MCP tool descriptions.
- **All responses are JSON strings** via `ok(data)` or `err(message)`, except `state_screenshot` which returns an MCP `Image` object when the compressed image fits inline (≤800 KB).
- **ruyiPage is synchronous** — every call goes through `run_sync()` which uses `asyncio.to_thread`.
- **Stale element recovery**: `resolve_element` in `runtime.py` catches element access failures and attempts re-query using the stored `locator_hint`.
- **Logging goes to stderr only** — stdout is the JSON-RPC transport channel.

### Dependencies

- **`ruyiPage`** (≥1.1.0) — Core Firefox BiDi automation library. Currently installed as editable from sibling directory `E:/git_project/ruyipage`.
- **`mcp`** — MCP SDK providing `FastMCP` server framework.
- **`Pillow`** — Screenshot compression (resize to max 1280px wide, JPEG at quality 72).

## Configuration

Priority (high → low): environment variables > `ruyipage_mcp.json` config file > built-in defaults.

Config file search: `RUYIPAGE_MCP_CONFIG` env var path → `./ruyipage_mcp.json` → defaults. The config file is JSON — see `ruyipage_mcp.example.json` for the template.

All defined in `config.py`.

| Config key / Env var | Default | Purpose |
|---|---|---|
| `browser_path` / `RUYIPAGE_MCP_BROWSER_PATH` | `E:\ruyi_firefox\firefox.exe` | Firefox executable path |
| `disable_run_js` / `RUYIPAGE_MCP_DISABLE_RUN_JS` | `false` | Disable `js_run` tool |
| `disable_extensions` / `RUYIPAGE_MCP_DISABLE_EXTENSIONS` | `false` | Disable extension support |
| `browser_path_whitelist` / `RUYIPAGE_MCP_BROWSER_PATH_WHITELIST` | `[]` (any) | Allowed browser paths |
| `max_elements` / `RUYIPAGE_MCP_MAX_ELEMENTS` | `512` | Per-session element LRU capacity |
| `event_buffer_size` / `RUYIPAGE_MCP_EVENT_BUFFER_SIZE` | `500` | BiDi event buffer size |
| `wait_timeout_ceiling` / `RUYIPAGE_MCP_WAIT_TIMEOUT_CEILING` | `60` | Hard ceiling (seconds) for wait timeouts |

## Implementation Notes

- `act_click` uses `ele.click.left()` (not `click_self()`) to avoid false-negative at coordinate (0,0).
- `act_input` with `clear=True` does native focus via `click.left()` then Ctrl+A+Delete through BiDi actions before calling `ele.input(text, clear=False)`.
- `net_collector` stores collector objects on `SessionEntry._collectors` (declared in `__slots__`, initialized in `__init__`).
- ruyiPage `ele.html` returns **outerHTML**. `dom_read` treats both `"html"` and `"outer_html"` as outerHTML; `"inner_html"` attempts `ele.inner_html` with fallback.
