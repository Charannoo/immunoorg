"""
War Room — JSON API only. The judge-facing UI lives on the Gradio **/demo** page
(accordion: Live LLM War Room).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.war_room_debate import run_war_room_debate

router = APIRouter(tags=["war-room"])


class WarRoomRequest(BaseModel):
    threat_type: str = Field(min_length=1)
    severity: int = Field(ge=1, le=10)
    source_ip: str = Field(min_length=1)
    target_service: str = Field(min_length=1)
    description: str = Field(min_length=1)
    preference_injection: str | None = None


@router.post("/api/war-room")
async def war_room_api(req: WarRoomRequest):
    try:
        return await run_war_room_debate(
            threat_type=req.threat_type,
            severity=req.severity,
            source_ip=req.source_ip,
            target_service=req.target_service,
            description=req.description,
            preference_injection=req.preference_injection,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e


__all__ = ["router", "WarRoomRequest"]
