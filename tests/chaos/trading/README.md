# Chaos tests — trading

These tests break things on purpose. Order execution is the part of the platform where a failure
costs money rather than a retry, so the failure paths need the same evidence as the happy path.

Each scenario asserts the *safe* outcome, which is usually a refusal or a parked order — never a
resubmission.

| Scenario | Required outcome |
| --- | --- |
| Venue times out mid-submit | Order becomes `unresolved`; **no automatic retry**; reconciliation asks the venue |
| Venue returns 5xx after accepting | Same as above — an ambiguous response is not a rejection |
| Duplicate confirm of one intent | Second call returns the first order; exactly one venue submission |
| Feed goes silent | Quotes go stale; the risk gate refuses to price; no order valued on a dead quote |
| Redis unavailable | Quote lookups fail closed; trading refuses rather than pricing on nothing |
| Venue rate-limits us | Backoff honoured; orders and cancels keep priority over backfill |
| Clock skew against venue time | Skew detected and reported; a future-stamped quote counts as stale |
| Kill switch engaged mid-flight | New submissions refused; in-flight orders reconciled, not abandoned |

## Rule

A chaos test that ends in "and then it retried" is a bug report, not a passing test. The only
component allowed to resolve an ambiguous submission is reconciliation, and the only authority on
whether an order exists is the venue.
