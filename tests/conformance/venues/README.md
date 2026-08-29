# Venue conformance suite

Every `VenueAdapter` implementation runs the **same** suite. That is the point of the abstraction:
if the paper adapter and the Binance adapter do not agree on what a rejected order looks like,
the code above them has to special-case venues, and the special cases are where the bugs live.

The suite itself is library code, not test code — it lives at
`shared/atlas_venues/conformance.py` so an out-of-tree adapter can import and run it. Add a file
here per adapter that wires the suite to a live or recorded connection:

| File | Status |
| --- | --- |
| `shared/tests/venues/test_paper_conformance.py` | passing — the reference implementation |
| `test_mt5_conformance.py` | not written; needs the Windows bridge sidecar |
| `test_oanda_conformance.py` | not written; needs a practice account |
| `test_binance_conformance.py` | not written; needs testnet keys |
| `test_bybit_conformance.py` | not written; needs testnet keys |
| `test_ibkr_conformance.py` | not written; needs IB Gateway + paper account |

## Rules for adding an adapter here

1. **The suite is not editable per venue.** If an adapter cannot pass a group, it declares the
   capability as unsupported and the suite skips that group explicitly — a skip names what is
   missing, an edited assertion hides it.
2. **No live-money account.** Testnet, demo, or practice only. A conformance run submits and
   cancels real orders.
3. **Credentials come from the environment, never the repo**, and only for the venue under test.
