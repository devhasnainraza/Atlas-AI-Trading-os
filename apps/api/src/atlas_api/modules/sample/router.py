"""Sample module v1 API + module definition."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from atlas_api.deps import get_runtime
from atlas_api.modules.public import EventSubscriptionDef, ModuleDef
from atlas_api.modules.sample import events
from atlas_api.modules.sample.router_v2 import router_v2
from atlas_api.modules.sample.schemas import EchoRequest, EchoResponse
from atlas_api.modules.sample.service import SampleService
from atlas_api.runtime import PlatformRuntime

router = APIRouter(prefix="/sample", tags=["sample"])


def get_service(runtime: PlatformRuntime = Depends(get_runtime)) -> SampleService:
    return SampleService(runtime.outbox, runtime.bus)


@router.post("/echo", response_model=EchoResponse)
async def echo(body: EchoRequest, service: SampleService = Depends(get_service)) -> EchoResponse:
    correlation_id = await service.echo(body.message)
    return EchoResponse(message=body.message, correlation_id=correlation_id)


@router.get("/guarded")
async def guarded_capability(runtime: PlatformRuntime = Depends(get_runtime)) -> dict[str, object]:
    """A capability behind a feature flag (US6) — safe default is OFF."""
    evaluation = runtime.flags.evaluate("sample.guarded_capability", default=False)
    return {"enabled": bool(evaluation.value), "reason": evaluation.reason}


def build_sample_module() -> ModuleDef:
    return ModuleDef(
        name="sample",
        version="1.0.0",
        owner="platform-team",
        router=router,
        routers_extra=(router_v2,),
        subscriptions=(
            EventSubscriptionDef(
                consumer="sample.echo_consumer",
                event_type="atlas.sample.echo.requested",
                handler=events.on_echo_requested,
            ),
        ),
    )
