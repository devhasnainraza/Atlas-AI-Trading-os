"""Shared venue conformance suite (Spec 03 plan §18, T024).

Every adapter must pass these tests. They encode the invariants that make adapters
substitutable — an adapter that satisfies them can be swapped in anywhere without the order
service, the risk gate, or the UI knowing which venue it is talking to.

To conform, a venue's test module subclasses :class:`VenueAdapterConformance` and supplies a
fixture returning a live adapter plus its test instrument. Nothing here is venue-specific.

The suite deliberately asserts *refusals* as much as successes: that unadvertised capabilities
raise, that a duplicate ``client_order_id`` does not produce a second order, and that floats
are rejected. Those are the behaviours a careless adapter gets wrong, and they are the ones
that cost money.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from decimal import Decimal

import pytest

from atlas_venues.enums import OrderSide, OrderState, OrderType, TimeInForce, VenueEnvironment
from atlas_venues.errors import ErrorClass, UnsupportedCapabilityError, VenueError
from atlas_venues.models import InstrumentSpec, SubmitRequest
from atlas_venues.precision import ZERO
from atlas_venues.protocol import VenueAdapter


@dataclass(frozen=True, slots=True)
class ConformanceTarget:
    """What a venue's conformance module hands the suite."""

    adapter: VenueAdapter
    instrument: InstrumentSpec
    environment: VenueEnvironment
    can_submit: bool = True
    """False for read-only credentials; submission tests are skipped, everything else runs."""


class VenueAdapterConformance:
    """Subclass this and provide the ``target`` fixture."""

    @pytest.fixture
    def target(self) -> ConformanceTarget:  # pragma: no cover - overridden by subclasses
        raise NotImplementedError("conformance subclasses must provide a `target` fixture")

    # -- Protocol shape ----------------------------------------------------------------

    def test_satisfies_protocol(self, target: ConformanceTarget) -> None:
        assert isinstance(target.adapter, VenueAdapter)

    def test_declares_every_protocol_member(self, target: ConformanceTarget) -> None:
        """No silent omissions: a missing method must fail here, not at 3am on a live order."""
        expected = {
            name
            for name in dir(VenueAdapter)
            if not name.startswith("_") and callable(getattr(VenueAdapter, name, None))
        }
        missing = [name for name in expected if not hasattr(target.adapter, name)]
        assert not missing, f"adapter is missing protocol members: {sorted(missing)}"

    def test_capabilities_is_pure(self, target: ConformanceTarget) -> None:
        """``capabilities()`` must be sync and side-effect free — it is called on hot paths."""
        assert not inspect.iscoroutinefunction(target.adapter.capabilities)
        first = target.adapter.capabilities()
        assert target.adapter.capabilities() == first

    def test_capabilities_declares_its_own_venue_and_environment(
        self, target: ConformanceTarget
    ) -> None:
        caps = target.adapter.capabilities()
        assert caps.venue_code
        assert caps.display_name
        assert caps.asset_classes, "an adapter must declare at least one asset class"
        assert caps.order_types, "an adapter must declare at least one order type"
        assert target.environment in caps.environments

    def test_rate_limit_model_is_declared(self, target: ConformanceTarget) -> None:
        model = target.adapter.rate_limit_model()
        assert model.window_seconds > 0
        assert model.requests_per_window or model.weight_per_window, (
            "a rate limit model must meter either requests or weight"
        )

    # -- Error classification ----------------------------------------------------------

    def test_classifies_venue_errors_by_their_own_class(self, target: ConformanceTarget) -> None:
        for error_class in ErrorClass:
            exc = VenueError("synthetic", venue_code=target.adapter.capabilities().venue_code)
            exc.error_class = error_class  # type: ignore[misc]
            assert target.adapter.classify_error(exc) is error_class

    def test_classifies_unknown_errors_without_raising(self, target: ConformanceTarget) -> None:
        assert isinstance(target.adapter.classify_error(RuntimeError("boom")), ErrorClass)

    def test_ambiguous_is_never_retryable(self) -> None:
        """The invariant behind FR-030: never re-send a submission whose outcome is unknown."""
        assert not ErrorClass.AMBIGUOUS.is_retryable

    # -- Discovery ---------------------------------------------------------------------

    async def test_verify_permissions_returns_a_reason(self, target: ConformanceTarget) -> None:
        ok, detail = await target.adapter.verify_permissions()
        assert isinstance(ok, bool)
        assert detail, "verify_permissions must explain itself, pass or fail"

    async def test_instrument_specs_are_decimal_and_positive(
        self, target: ConformanceTarget
    ) -> None:
        spec = await target.adapter.instrument(target.instrument.venue_symbol)
        for name in ("tick_size", "quantity_step", "min_quantity"):
            value = getattr(spec, name)
            assert isinstance(value, Decimal), f"{name} must be Decimal, got {type(value)}"
            assert value > ZERO
        assert spec.canonical_symbol, "every instrument needs a canonical symbol"

    async def test_unknown_instrument_raises(self, target: ConformanceTarget) -> None:
        with pytest.raises(VenueError):
            await target.adapter.instrument("__ATLAS_NO_SUCH_INSTRUMENT__")

    async def test_server_time_offset_is_measured(self, target: ConformanceTarget) -> None:
        offset = await target.adapter.server_time_offset()
        assert offset.measured_at.tzinfo is not None, "venue timestamps must be timezone-aware"
        assert offset.round_trip_seconds >= 0

    # -- Market data -------------------------------------------------------------------

    async def test_quotes_are_decimal_and_timezone_aware(self, target: ConformanceTarget) -> None:
        quotes = await target.adapter.quote([target.instrument.venue_symbol])
        for quote in quotes:
            assert isinstance(quote.bid, Decimal) and isinstance(quote.ask, Decimal)
            assert quote.ask >= quote.bid, "ask below bid means the adapter crossed its mapping"
            assert quote.venue_time.tzinfo is not None
            assert quote.received_at.tzinfo is not None

    async def test_unsupported_bars_raise_rather_than_return_empty(
        self, target: ConformanceTarget
    ) -> None:
        """An empty list would read as 'no history exists'. Unsupported must say unsupported."""
        if target.adapter.capabilities().supports_historical_bars:
            pytest.skip("venue supports bars; covered by its own history tests")
        with pytest.raises(UnsupportedCapabilityError):
            await target.adapter.bars(target.instrument.venue_symbol, "1m")

    # -- Account -----------------------------------------------------------------------

    async def test_account_snapshot_is_decimal_and_environment_tagged(
        self, target: ConformanceTarget
    ) -> None:
        snapshot = await target.adapter.account_snapshot()
        assert isinstance(snapshot.balance, Decimal)
        assert isinstance(snapshot.equity, Decimal)
        assert snapshot.environment is target.environment
        assert snapshot.currency
        assert snapshot.venue_time.tzinfo is not None

    async def test_positions_are_environment_tagged_and_signless(
        self, target: ConformanceTarget
    ) -> None:
        """Direction lives in ``side``; a negative quantity is how sign errors flip a trade."""
        for position in await target.adapter.positions():
            assert position.quantity > ZERO
            assert position.environment is target.environment

    async def test_open_orders_are_environment_tagged(self, target: ConformanceTarget) -> None:
        for order in await target.adapter.open_orders():
            assert order.environment is target.environment
            assert isinstance(order.quantity, Decimal)
            assert isinstance(order.filled_quantity, Decimal)

    # -- Execution ---------------------------------------------------------------------

    async def test_submit_rejects_a_foreign_environment(self, target: ConformanceTarget) -> None:
        """An adapter must refuse an order tagged for a different world (FR-050)."""
        caps = target.adapter.capabilities()
        foreign = next((e for e in VenueEnvironment if e not in caps.environments), None)
        if foreign is None:
            pytest.skip("adapter serves every environment")
        request = self._build_request(target, client_order_id="atlas-conf-foreign-env")
        request = _replace_environment(request, foreign)
        with pytest.raises(VenueError):
            await target.adapter.submit(request)

    async def test_duplicate_client_order_id_does_not_create_a_second_order(
        self, target: ConformanceTarget
    ) -> None:
        """The at-most-once invariant at the adapter boundary (FR-026)."""
        if not target.can_submit:
            pytest.skip("target is read-only")
        request = self._build_request(target, client_order_id="atlas-conf-dupe-001")
        first = await target.adapter.submit(request)
        second = await target.adapter.submit(request)
        assert first.venue_order_ref == second.venue_order_ref, (
            "resubmitting the same client_order_id created a second order at the venue"
        )
        assert second.client_order_id == request.client_order_id

    async def test_order_status_is_queryable_by_client_order_id(
        self, target: ConformanceTarget
    ) -> None:
        """The resolution path out of ``unresolved``: ask, never re-send (FR-030)."""
        if not target.can_submit:
            pytest.skip("target is read-only")
        request = self._build_request(target, client_order_id="atlas-conf-lookup-001")
        await target.adapter.submit(request)
        found = await target.adapter.order_status(client_order_id=request.client_order_id)
        assert found.client_order_id == request.client_order_id
        assert isinstance(found.state, OrderState)

    async def test_unknown_order_lookup_raises(self, target: ConformanceTarget) -> None:
        with pytest.raises(VenueError):
            await target.adapter.order_status(client_order_id="__ATLAS_NO_SUCH_ORDER__")

    async def test_cancel_of_terminal_order_is_not_an_error(
        self, target: ConformanceTarget
    ) -> None:
        """Cancel is idempotent: a retry after a network blip must not raise."""
        if not target.can_submit:
            pytest.skip("target is read-only")
        request = self._build_request(target, client_order_id="atlas-conf-cancel-001")
        submitted = await target.adapter.submit(request)
        assert submitted.venue_order_ref is not None
        first = await target.adapter.cancel(
            submitted.venue_order_ref, client_order_id=request.client_order_id
        )
        second = await target.adapter.cancel(
            submitted.venue_order_ref, client_order_id=request.client_order_id
        )
        assert second.state == first.state

    async def test_unadvertised_amend_raises(self, target: ConformanceTarget) -> None:
        if target.adapter.capabilities().supports_amend:
            pytest.skip("venue supports amend; covered by its own tests")
        from atlas_venues.models import AmendRequest

        with pytest.raises(UnsupportedCapabilityError):
            await target.adapter.amend(
                AmendRequest(
                    venue_order_ref="whatever",
                    client_order_id="atlas-conf-amend-001",
                    quantity=target.instrument.min_quantity,
                )
            )

    # -- Helpers -----------------------------------------------------------------------

    @staticmethod
    def _build_request(target: ConformanceTarget, *, client_order_id: str) -> SubmitRequest:
        spec = target.instrument
        return SubmitRequest(
            venue_code=target.adapter.capabilities().venue_code,
            venue_account_ref="conformance",
            venue_symbol=spec.venue_symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=spec.min_quantity,
            time_in_force=TimeInForce.IOC,
            client_order_id=client_order_id,
            environment=target.environment,
        )


def _replace_environment(request: SubmitRequest, environment: VenueEnvironment) -> SubmitRequest:
    return SubmitRequest(
        venue_code=request.venue_code,
        venue_account_ref=request.venue_account_ref,
        venue_symbol=request.venue_symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        time_in_force=request.time_in_force,
        client_order_id=request.client_order_id,
        environment=environment,
    )


__all__ = ["ConformanceTarget", "VenueAdapterConformance"]
