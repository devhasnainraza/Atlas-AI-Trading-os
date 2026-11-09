"""Time-ordered identifier generation (UUIDv7, RFC 9562).

Every Atlas primary key and event id is a UUIDv7 rather than a v4. The reason is index
locality: a v4 key inserts at a random point in the B-tree, so a write-heavy table keeps
paging in cold index blocks and the index bloats. A v7 key is monotonic, so inserts append
to the right-hand edge and range scans on "recent rows" become sequential reads.

The secondary benefit is that an id carries its own creation time, which makes debugging a
production incident possible from an id alone — no join against ``created_at`` required.
"""

from __future__ import annotations

import os
import threading
import time
import uuid

_lock = threading.Lock()
_last = 0


def uuid7() -> uuid.UUID:
    """A UUIDv7: 48-bit unix-millisecond prefix, version nibble, random tail.

    Strictly monotonic within the process. Random tails alone do not sort *within* a
    millisecond, and two rows created in the same millisecond with an arbitrary order
    break "sort by id" as a stand-in for "sort by creation time" — so a process-local
    guard bumps the value, the counter technique RFC 9562 §6.2 method 2 describes.

    Not monotonic *across* processes: two API workers can mint ids a hair out of order.
    That is acceptable for index locality (they still land in the same page range) and is
    why nothing in Atlas treats id ordering as a distributed happens-before relation.
    """
    global _last
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ts_ms << 80) | (0x7 << 76) | (rand & ((1 << 76) - 1))
    with _lock:
        if value <= _last:
            value = _last + 1
        _last = value
    return uuid.UUID(int=value)


def uuid7_str() -> str:
    """``uuid7()`` as a canonical hyphenated string, for JSON and event payloads."""
    return str(uuid7())


def uuid7_timestamp_ms(value: uuid.UUID) -> int:
    """Extract the creation millisecond from a UUIDv7.

    Raises ``ValueError`` on a non-v7 input rather than returning a meaningless number —
    a v4 read as a timestamp yields a date in the year 40000 and sends whoever is reading
    the logs down a long dead end.
    """
    if value.version != 7:
        raise ValueError(f"not a UUIDv7 (version={value.version})")
    return value.int >> 80


__all__ = ["uuid7", "uuid7_str", "uuid7_timestamp_ms"]
