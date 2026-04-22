"""
routers/events.py
-----------------
Routes HTTP pour les événements.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

import aiosqlite

from database import get_db
from models import EventCreate, EventPatch, EventResponse, EventListResponse
from services import event_service

router = APIRouter(prefix="/events", tags=["events"])

DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(body: EventCreate, db: DbDep):
    return await event_service.create_event(db, body)


@router.get("", response_model=EventListResponse)
async def list_events(
    db: DbDep,
    user_id: str | None                          = Query(None),
    kind:    Annotated[list[str] | None, Query()] = None,
    tag:     Annotated[list[str] | None, Query()] = None,
    from_:   str | None                           = Query(None, alias="from"),
    to:      str | None                           = Query(None),
    limit:   int                                  = Query(50, ge=1, le=500),
    cursor:  str | None                           = Query(None),
):
    return await event_service.list_events(
        db,
        user_id=user_id,
        kinds=kind,
        tags=tag,
        from_dt=from_,
        to_dt=to,
        limit=limit,
        cursor=cursor,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: DbDep):
    return await event_service.get_event(db, event_id)


@router.patch("/{event_id}", response_model=EventResponse)
async def patch_event(event_id: int, request: Request, body: EventPatch, db: DbDep):
    # On passe le body brut pour distinguer "champ absent" de "champ null"
    raw_body = await request.json()
    return await event_service.patch_event(db, event_id, body, raw_body)


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int, db: DbDep):
    await event_service.delete_event(db, event_id)
    # 204 No Content : pas de body