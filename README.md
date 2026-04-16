# ruyipage-mcp

MCP server that exposes [ruyiPage](https://github.com/LoseNine/ruyipage) Firefox automation as Claude Code tools.

## Install

```bash
pip install -e .
```

## Usage

### Claude Code `.mcp.json`

```json
{
  "mcpServers": {
    "ruyipage": {
      "command": "python",
      "args": ["-m", "ruyipage_mcp"]
    }
  }
}
```

### CLI

```bash
claude mcp add --scope user ruyipage python -- -m ruyipage_mcp
```

## Tools (34)

| Namespace | Tools |
|-----------|-------|
| `session` | launch, attach, auto_attach, quit |
| `nav` | get, back, forward, refresh, info |
| `dom` | find, find_all, read, query_in, wait_for, release |
| `act` | click, input, simple, chain |
| `state` | screenshot, save_pdf, cookies, storage |
| `js` | run, preload |
| `net` | intercept, listen, collector, headers, cache |
| `ctx` | tabs, emulation, events |
| `meta` | describe_capabilities |
