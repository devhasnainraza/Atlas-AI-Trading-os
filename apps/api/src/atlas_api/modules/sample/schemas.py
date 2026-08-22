"""Sample module request/response schemas — strict validation (FR-010)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EchoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500)


class EchoResponse(BaseModel):
    message: str
    correlation_id: str


class EchoResponseV2(BaseModel):
    """v2 shape — breaking change lives only here; v1 clients are untouched (FR-012)."""

    echo: dict[str, str]
    correlation_id: str
