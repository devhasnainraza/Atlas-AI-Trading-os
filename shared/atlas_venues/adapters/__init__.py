"""Venue adapter implementations.

Every adapter in this package implements :class:`atlas_venues.protocol.VenueAdapter` and is
verified by the shared conformance suite. :mod:`atlas_venues.adapters.paper` is the reference
implementation: it is fully deterministic, needs no network, and is what the conformance suite
itself is validated against.
"""

from atlas_venues.adapters.paper import PaperAdapter, PaperEngine, PaperFillModel

__all__ = ["PaperAdapter", "PaperEngine", "PaperFillModel"]
