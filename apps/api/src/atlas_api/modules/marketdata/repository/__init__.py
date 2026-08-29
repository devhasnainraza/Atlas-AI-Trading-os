"""Market data persistence ports — quote cache, bar store, subscription registry.

Ports are Protocols with in-memory reference implementations, matching the Spec 00 pattern
(``InMemoryOutbox``, ``InMemoryAuditLog``). The Postgres/Redis implementations land behind the
same interfaces without touching a caller.
"""
