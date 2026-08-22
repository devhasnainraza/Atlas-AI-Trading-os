"""Sample module v2 API — proves versioned coexistence (FR-012, US4).

The v2 response shape is a breaking change relative to v1; both run side by side and v1
clients are unaffected.
"""

from __future__ import annotations

from fastapi import APIRouter

from atlas_api.modules.sample.schemas import EchoRequest, EchoResponseV2
from atlas_core.correlation import get_correlation_id

router_v2 = APIRouter(prefix="/sample", tags=["sample-v2"])


@router_v2.post("/echo", response_model=EchoResponseV2)
async def echo_v2(body: EchoRequest) -> EchoResponseV2:
    return EchoResponseV2(echo={"message": body.message}, correlation_id=get_correlation_id())


# Marker used by the app factory to mount this router under /v2 instead of /v1.
router_v2.version = "v2"  # type: ignore[attr-defined]
