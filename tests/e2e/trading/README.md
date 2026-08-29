# End-to-end tests — trading

Full-stack runs against a booted local stack (`infra/docker`), following
[quickstart.md](../../../specs/003-trading-integration/quickstart.md). Like the existing
`tests/e2e/test_local_stack.py`, these skip rather than fail when the stack is not reachable — a
developer running the unit suite should not have to boot Postgres and Kafka first.

Journeys to cover:

1. Connect the paper venue → verify capabilities → list accounts → healthy.
2. Subscribe to a symbol → receive quotes over SSE → quote goes stale when the feed stops.
3. Create an order intent → read the risk verdict and its `verdict_hash` → confirm → filled.
4. Confirm the same intent twice → one order, one venue submission.
5. Breach a policy limit → refused with the failing rule named, and nothing submitted.
6. Reset the paper book → balance restored, reset count incremented, audit history intact.
7. Run reconciliation with a seeded discrepancy → venue state wins, discrepancy recorded.

## Rule

`PAPER` environment only. An e2e suite that can reach a live venue will eventually reach one on a
branch nobody reviewed.
