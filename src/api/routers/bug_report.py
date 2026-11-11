"""Router zgłoszeń błędów („Report bug") — zrzut + opis zapisywane na dysku hosta.

Sprawa stołu, nie akcja gry: stan gry się NIE zmienia (bez commitu i broadcastu). Zgłosić może
każdy gracz z miejscem (w sieci tożsamość z tokenu — gość bez miejsca dostaje 403) oraz host.
Brak katalogu raportów (np. testy bez ``bug_reports_dir``) => 503; zły zrzut => 422.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.actor import ActorId
from src.api.bug_reports import BugReportInput, write_bug_report
from src.api.context import AppContext, get_ctx

router = APIRouter(prefix="/bug-report", tags=["bug-report"])


class BugReportRequest(BaseModel):
    """Zgłoszenie z przeglądarki."""

    description: str = Field(default="", max_length=10_000)
    screenshot: str | None = Field(default=None, description="data:image/png;base64,...")
    client: dict[str, Any] = Field(default_factory=dict)


class BugReportResponse(BaseModel):
    """Nazwa katalogu, w którym leży raport (względem katalogu raportów hosta)."""

    report_id: str


@router.post("", response_model=BugReportResponse)
async def post_bug_report(
    actor: ActorId, request: BugReportRequest, ctx: AppContext = Depends(get_ctx)
) -> BugReportResponse:
    """Zapisuje zgłoszenie (opis + zrzut + pełny stan) w nowym katalogu raportu."""
    if ctx.bug_reports_dir is None:
        raise HTTPException(status_code=503, detail="Bug reports are not enabled on this server.")
    if not request.description.strip() and request.screenshot is None:
        raise HTTPException(status_code=422, detail="Describe the problem or attach a screenshot.")
    try:
        folder = write_bug_report(
            ctx.bug_reports_dir,
            state=ctx.service.current_state(),
            actor=actor,  # kto zgłasza (w sieci: gracz z tokenu, RULES.md 44.1a)
            report=BugReportInput(
                description=request.description,
                screenshot=request.screenshot,
                client=request.client,
            ),
            now=ctx.service.now(),
            save_name=ctx.save_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    print(f"[bug-report] New report: {folder}")
    return BugReportResponse(report_id=folder.name)
