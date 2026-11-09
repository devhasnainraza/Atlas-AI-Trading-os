"""Worker event consumers (Spec 02+).

Each consumer subscribes to the event types it acts on and is registered onto a bus at
worker startup. Handlers are written to the bus's contract: raise on a transient failure and
the bus retries then dead-letters (see ``atlas_events.bus``); return normally to acknowledge.
"""
