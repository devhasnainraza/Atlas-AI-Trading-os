"""The paper adapter must pass the shared conformance suite (T024, T108)."""

from __future__ import annotations

import pytest

from atlas_venues.adapters.paper import PaperAdapter
from atlas_venues.conformance import ConformanceTarget, VenueAdapterConformance
from atlas_venues.enums import VenueEnvironment
from atlas_venues.models import InstrumentSpec


class TestPaperAdapterConformance(VenueAdapterConformance):
    """The reference implementation. If the suite is wrong, it is wrong here first."""

    @pytest.fixture
    def target(self, paper_adapter: PaperAdapter, btc_spec: InstrumentSpec) -> ConformanceTarget:
        return ConformanceTarget(
            adapter=paper_adapter,
            instrument=btc_spec,
            environment=VenueEnvironment.PAPER,
        )
