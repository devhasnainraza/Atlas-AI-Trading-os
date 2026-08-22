# Module template

Copy this directory to `apps/api/src/atlas_api/modules/<your_module>/` and fill it in.
Rules (enforced by import-linter in CI):

1. Other modules may import ONLY your `public.py`.
2. Layers depend inward: router → service → domain; repositories implement domain ports.
3. Publish events through the outbox in your service layer; consume by declaring
   `EventSubscriptionDef`s in your `ModuleDef`. Handlers must be idempotent
   (`atlas_events.ledger.idempotent`).
4. Register new event types in `shared/atlas_events/catalog.py` AND the event catalog doc
   before first publish.
5. Add your module to `create_app` in `main.py` — one line; nothing else changes.

Layout:

```text
<your_module>/
├── __init__.py      # module docstring
├── public.py        # build_<module>_module() -> ModuleDef  ← only legal import surface
├── router.py        # API layer (thin; declares ModuleDef)
├── schemas.py       # Pydantic request/response models (extra="forbid" on writes)
├── service.py       # use cases; only layer that touches repos + publishes events
├── events.py        # event handlers this module consumes
├── domain/          # entities, value objects, domain errors (framework-free)
└── repository/      # adapters implementing domain ports
```
