# -*- coding: utf-8 -*-
"""Session and element registries.

SessionRegistry  — maps session_id (host:port) to FirefoxPage instances.
ElementRegistry  — maps short string IDs to FirefoxElement handles (per-session, LRU).
"""

import time
import uuid
import threading
from collections import OrderedDict

from . import config


# ---------------------------------------------------------------------------
# Element registry (per-session)
# ---------------------------------------------------------------------------

class ElementEntry(object):
    __slots__ = ("handle", "locator_hint", "created_at", "last_touched_at")

    def __init__(self, handle, locator_hint=None):
        self.handle = handle
        self.locator_hint = locator_hint
        now = time.time()
        self.created_at = now
        self.last_touched_at = now

    def touch(self):
        self.last_touched_at = time.time()


class ElementRegistry(object):
    """LRU-bounded element handle registry."""

    def __init__(self):
        self._elements = OrderedDict()
        self._lock = threading.Lock()

    # -- mutators --

    def add(self, handle, locator_hint=None):
        eid = "el_" + uuid.uuid4().hex[:6]
        with self._lock:
            cap = config.max_elements()
            while len(self._elements) >= cap:
                self._elements.popitem(last=False)
            self._elements[eid] = ElementEntry(handle, locator_hint)
        return eid

    def remove(self, element_id):
        with self._lock:
            return self._elements.pop(element_id, None)

    def clear(self):
        with self._lock:
            self._elements.clear()

    # -- accessors --

    def get(self, element_id):
        with self._lock:
            entry = self._elements.get(element_id)
            if entry is None:
                return None
            entry.touch()
            self._elements.move_to_end(element_id)
            return entry

    def __len__(self):
        return len(self._elements)

    def summary(self):
        with self._lock:
            return {"count": len(self._elements), "ids": list(self._elements.keys())[:20]}


# ---------------------------------------------------------------------------
# Session registry (global singleton)
# ---------------------------------------------------------------------------

class SessionEntry(object):
    __slots__ = ("page", "owned", "created_at", "last_used_at", "elements", "_collectors")

    def __init__(self, page, owned=True):
        self.page = page
        self.owned = owned
        now = time.time()
        self.created_at = now
        self.last_used_at = now
        self.elements = ElementRegistry()
        self._collectors = {}

    def touch(self):
        self.last_used_at = time.time()


class SessionRegistry(object):
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()

    def add(self, session_id, page, owned=True):
        with self._lock:
            self._sessions[session_id] = SessionEntry(page, owned)

    def get(self, session_id):
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry:
                entry.touch()
            return entry

    def remove(self, session_id):
        with self._lock:
            entry = self._sessions.pop(session_id, None)
            if entry:
                entry.elements.clear()
            return entry

    def list_ids(self):
        with self._lock:
            return list(self._sessions.keys())

    def summary(self):
        with self._lock:
            return {
                sid: {
                    "owned": e.owned,
                    "elements": len(e.elements),
                }
                for sid, e in self._sessions.items()
            }

    def __len__(self):
        return len(self._sessions)

    def resolve(self, session_id=None):
        """Resolve a session_id to a SessionEntry.

        If *session_id* is None and exactly one session exists, auto-resolve.
        Returns (session_id, SessionEntry) or raises ValueError.
        """
        with self._lock:
            if session_id is not None:
                entry = self._sessions.get(session_id)
                if entry is None:
                    raise ValueError("session '{}' not found — active: {}".format(
                        session_id, list(self._sessions.keys())))
                entry.touch()
                return session_id, entry

            if len(self._sessions) == 1:
                sid, entry = next(iter(self._sessions.items()))
                entry.touch()
                return sid, entry

            if len(self._sessions) == 0:
                raise ValueError("no active sessions — call session_launch or session_attach first")

            raise ValueError(
                "multiple sessions active ({}); pass session_id explicitly".format(
                    list(self._sessions.keys())))


# Global instance
sessions = SessionRegistry()
