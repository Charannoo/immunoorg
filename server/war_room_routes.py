"""
War Room — HTML page and JSON API (minimal wiring for FastAPI app).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from server.war_room_debate import run_war_room_debate

router = APIRouter(tags=["war-room"])
_HTML_PATH = Path(__file__).resolve().parent / "war_room_page.html"


class WarRoomRequest(BaseModel):
    threat_type: str = Field(min_length=1)
    severity: int = Field(ge=1, le=10)
    source_ip: str = Field(min_length=1)
    target_service: str = Field(min_length=1)
    description: str = Field(min_length=1)
    preference_injection: str | None = None


@router.get("/war-room", response_class=HTMLResponse)
async def war_room_page():
    if not _HTML_PATH.is_file():
        raise HTTPException(status_code=500, detail="war_room_page.html missing")
    return HTMLResponse(_HTML_PATH.read_text(encoding="utf-8"))


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
