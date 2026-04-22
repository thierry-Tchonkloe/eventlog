"""
services/event_service.py

"""

import base64
import json
from datetime import datetime, timezone
from sqlite3 import IntegrityError

import aiosqlite

from exceptions import DuplicateEventError, NotFoundError, ValidationError
from models import EventCreate, EventPatch, EventResponse, EventListResponse, parse_and_normalize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _encode_cursor(occurred_at_utc: str, event_id: int) -> str:
    data = json.dumps({"o": occurred_at_utc, "i": event_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(data.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, int]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return data["o"], data["i"]
    except Exception:
        raise ValidationError("invalid pagination cursor")


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

async def create_event(db: aiosqlite.Connection, body: EventCreate) -> EventResponse:
    occurred_at_utc, occurred_at_raw = parse_and_normalize(body.occurred_at)
    recorded_at = _now_utc()
    tags_json = json.dumps(body.tags if body.tags else [], separators=(",", ":"))
    payload_json = json.dumps(body.payload, separators=(",", ":")) if body.payload else None

    try:
        async with db.execute(
            """
            INSERT INTO events
                (user_id, occurred_at_utc, occurred_at_raw, recorded_at, kind, tags, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (body.user_id, occurred_at_utc, occurred_at_raw,
             recorded_at, body.kind.value, tags_json, payload_json),
        ) as cur:
            new_id = cur.lastrowid
        await db.commit()
    except IntegrityError:
        # La contrainte UNIQUE(user_id, occurred_at_utc) a été violée. -> C'est la seule IntegrityError possible ici → 409 garanti (spec §8).
        raise DuplicateEventError(
            f"an event for user '{body.user_id}' at '{body.occurred_at}' already exists"
        )

    return await get_event(db, new_id)


# ---------------------------------------------------------------------------
# READ ONE
# ---------------------------------------------------------------------------

async def get_event(db: aiosqlite.Connection, event_id: int) -> EventResponse:
    async with db.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        raise NotFoundError(f"event {event_id} not found")

    return EventResponse.from_row(row)


# ---------------------------------------------------------------------------
# LIST + FILTER + CURSOR
# ---------------------------------------------------------------------------

async def list_events(
    db: aiosqlite.Connection,
    *,
    user_id:  str | None       = None,
    kinds:    list[str] | None = None,
    tags:     list[str] | None = None,
    from_dt:  str | None       = None,
    to_dt:    str | None       = None,
    limit:    int              = 50,
    cursor:   str | None       = None,
) -> EventListResponse:

    if limit < 1 or limit > 500:
        raise ValidationError("limit must be between 1 and 500")

    # Normalisation des timestamps de filtre
    from_utc = to_utc = None
    if from_dt:
        from_utc, _ = parse_and_normalize(from_dt)
    if to_dt:
        to_utc, _ = parse_and_normalize(to_dt)

    # Décodage du curseur (position de la dernière page)
    cursor_occ = cursor_id = None
    if cursor:
        cursor_occ, cursor_id = _decode_cursor(cursor)

    # Construction dynamique du WHERE
    conditions = []
    params: list = []

    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)

    if kinds:
        placeholders = ",".join("?" * len(kinds))
        conditions.append(f"kind IN ({placeholders})")
        params.extend(kinds)

    if from_utc:
        conditions.append("occurred_at_utc >= ?")
        params.append(from_utc)

    if to_utc:
        conditions.append("occurred_at_utc <= ?")
        params.append(to_utc)

    # Filtre tags : AND sémantique — chaque tag doit être présent (spec §5)
    # On utilise json_each() de SQLite pour interroger le tableau JSON.
    for tag in (tags or []):
        conditions.append(
            "EXISTS (SELECT 1 FROM json_each(events.tags) WHERE value = ?)"
        )
        params.append(tag)

    # Keyset pagination : on reprend après le dernier élément vu
    # Tri : occurred_at_utc DESC, id DESC
    # Condition "page suivante" : (occ < cursor_occ) OR (occ = cursor_occ AND id < cursor_id)
    if cursor_occ is not None:
        conditions.append(
            "(occurred_at_utc < ? OR (occurred_at_utc = ? AND id < ?))"
        )
        params.extend([cursor_occ, cursor_occ, cursor_id])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # On fetche limit+1 pour savoir s'il y a une page suivante
    query = f"""
        SELECT * FROM events
        {where}
        ORDER BY occurred_at_utc DESC, id DESC
        LIMIT ?
    """
    params.append(limit + 1)

    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    events = [EventResponse.from_row(r) for r in rows]

    next_cursor = None
    if has_next and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last["occurred_at_utc"], last["id"])

    return EventListResponse(
        event_count=len(events),
        events=events,
        next_cursor=next_cursor,
    )


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------

async def patch_event(
    db: aiosqlite.Connection,
    event_id: int,
    body: EventPatch,
    raw_body: dict,
) -> EventResponse:
    # Vérification existence (spec §8 : PATCH sur inexistant → 404)
    await get_event(db, event_id)

    fields = body.provided_fields(raw_body)
    if not fields:
        # Rien à mettre à jour → on retourne l'événement inchangé
        return await get_event(db, event_id)

    set_clauses = []
    params = []

    if "kind" in fields and fields["kind"] is not None:
        set_clauses.append("kind = ?")
        params.append(fields["kind"].value if hasattr(fields["kind"], "value") else fields["kind"])

    if "tags" in fields:
        tags_val = fields["tags"]
        set_clauses.append("tags = ?")
        params.append(json.dumps(tags_val if tags_val else [], separators=(",", ":")))

    if "payload" in fields:
        payload_val = fields["payload"]
        set_clauses.append("payload = ?")
        params.append(
            json.dumps(payload_val, separators=(",", ":")) if payload_val is not None else None
        )

    if not set_clauses:
        return await get_event(db, event_id)

    params.append(event_id)
    await db.execute(
        f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    await db.commit()

    return await get_event(db, event_id)


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

async def delete_event(db: aiosqlite.Connection, event_id: int) -> None:

    await get_event(db, event_id)  # lève NotFoundError si absent

    await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    await db.commit()