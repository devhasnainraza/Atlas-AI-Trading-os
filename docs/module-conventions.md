# Module conventions

Every capability is a module in `apps/api/src/atlas_api/modules/<name>/`.

## Required files

| File | Purpose |
|---|---|
| `__init__.py` | Module docstring |
| `public.py` | `build_<name>_module() → ModuleDef` — the ONLY legal import surface |
| `router.py` | API layer (thin); declares `ModuleDef` at the bottom |
| `schemas.py` | Pydantic request/response models; **`extra="forbid"` on writes** |
| `service.py` | Use cases; the only layer that touches repos and publishes events |
| `events.py` | Event handler functions consumed by the module |
| `domain/` | Entities, value objects, domain errors (no framework imports) |
| `repository/` | Adapters implementing domain protocols |

## Contract rules

1. **No plaintext secrets, tokens, or PII in logs** — structlog's redaction filter covers
   known key names; never pass raw values as positional args.
2. **Event handlers must be idempotent** — use `atlas_events.ledger.idempotent`.
3. **Register event types before publish** — add to `atlas_events/catalog.py` and the
   events contract doc; unknown types fail `InMemoryEventBus.publish`.
4. **Fail-fast config** — declare all required settings in a `pydantic_settings.BaseSettings`
   subclass; no `os.environ.get("X", "default")` for security-relevant values.
5. **Correlation IDs** — never call `datetime.now()` or `uuid.uuid4()` directly in domain
   code; use `atlas_core.correlation.get_correlation_id()` for identity, and the clock
   abstraction for time (enables deterministic tests).

## Review checklist

- [ ] `public.py` only exposes `build_<name>_module()`
- [ ] No import of another module's internals
- [ ] New event types registered in catalog + events contract doc
- [ ] `extra="forbid"` on write schemas
- [ ] Handlers wrapped with `idempotent`
- [ ] No secrets / correlation ID bypasses in domain code
- [ ] Tests cover the story's acceptance scenarios
