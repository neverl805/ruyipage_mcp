# -*- coding: utf-8 -*-
"""Server entry point — imports all tool modules to register them, then exposes run()."""

import sys
import atexit
import logging

from .app import mcp
from .registries import sessions

# Import tool modules so their @mcp.tool() decorators execute
from .tools import session  # noqa: F401
from .tools import nav      # noqa: F401
from .tools import dom      # noqa: F401
from .tools import act      # noqa: F401
from .tools import state    # noqa: F401
from .tools import js       # noqa: F401
from .tools import net      # noqa: F401
from .tools import ctx      # noqa: F401
from .tools import meta     # noqa: F401

# Configure logging to stderr (stdout is reserved for JSON-RPC in stdio mode)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [ruyipage-mcp] %(levelname)s %(message)s",
)
logger = logging.getLogger("ruyipage-mcp")


def _cleanup():
    """atexit handler: quit all owned browser sessions."""
    for sid in list(sessions.list_ids()):
        entry = sessions.get(sid)
        if entry and entry.owned:
            try:
                entry.page.quit()
                logger.info("cleaned up owned session %s", sid)
            except Exception:
                pass
        sessions.remove(sid)


atexit.register(_cleanup)


def run():
    """Start the MCP server (stdio transport)."""
    logger.info("ruyipage-mcp starting (stdio)")
    mcp.run(transport="stdio")
