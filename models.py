"""
models.py
---------
Modèles Pydantic pour les requêtes et réponses de l'API, ainsi que des fonctions
"""

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from dateutil import parser as dtparser
from dateutil.parser import ParserError
from pydantic import BaseModel, field_validator, model_validator, Field

from exceptions import ValidationError, PayloadTooLargeError


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PAYLOAD_MAX_BYTES = 4 * 1024  # 4 KB
TAG_PATTERN = re.compile(r'^[a-z0-9_-]{1,32}$')
USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')
MAX_TAGS = 16


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class EventKind(str, Enum):
    click    = "click"
    view     = "view"
    purchase = "purchase"
    signup   = "signup"
    custom   = "custom"


# ---------------------------------------------------------------------------
# Helpers timestamps
# ---------------------------------------------------------------------------

def parse_and_normalize(raw: str) -> tuple[str, str]:

    try:
        dt = dtparser.parse(raw)
    except (ParserError, ValueError, OverflowError):
        raise ValidationError(f"occurred_at: invalid datetime format '{raw}'")

    if dt.tzinfo is None:
        raise ValidationError(
            "occurred_at: timezone required — "
            "use Z or an explicit offset like +05:30"
        )

    # Normalisation UTC
    utc = dt.astimezone(timezone.utc)
    occurred_at_utc = utc.isoformat()  # "2026-04-21T14:30:00+00:00"

    return occurred_at_utc, raw  # raw préservé tel quel


# ---------------------------------------------------------------------------
# Validation tags (réutilisée dans Create et Patch)
# ---------------------------------------------------------------------------

def validate_tags_field(v: Any) -> list[str] | None:

    if v is None:
        return None

    # Piège : Pydantic peut recevoir n'importe quel type JSON ici
    if not isinstance(v, list):
        raise ValueError(
            "must be a JSON array of strings — "
            "a bare string is not auto-coerced"
        )

    if len(v) == 0:
        raise ValueError(
            "empty array is rejected — omit the field instead"
        )

    if len(v) > MAX_TAGS:
        raise ValueError(f"max {MAX_TAGS} tags per event, got {len(v)}")

    for tag in v:
        if not isinstance(tag, str):
            raise ValueError(f"each tag must be a string, got {type(tag).__name__}")
        if not TAG_PATTERN.match(tag):
            raise ValueError(
                f"invalid tag '{tag}': "
                "must be 1-32 chars, lowercase, [a-z0-9_-] only"
            )

    if len(v) != len(set(v)):
        dupes = [t for t in v if v.count(t) > 1]
        raise ValueError(f"duplicate tags are not allowed: {list(set(dupes))}")

    return v


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    user_id:     str
    occurred_at: str
    kind:        EventKind
    tags:        Any = None   # Any pour intercepter string, int, etc.
    payload:     dict | None = None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not USER_ID_PATTERN.match(v):
            raise ValueError(
                "must be 1-64 chars, alphanumeric and underscore only"
            )
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> list[str] | None:
        return validate_tags_field(v)

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        size = len(json.dumps(v, separators=(",", ":")))
        if size > PAYLOAD_MAX_BYTES:
            raise ValueError(
                f"payload exceeds 4 KB limit ({size} bytes serialized)"
            )
        return v

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, v: str) -> str:

        parse_and_normalize(v)  # lève ValidationError si invalide
        return v


class EventPatch(BaseModel):

    kind:    EventKind | None = None
    tags:    Any              = None
    payload: dict | None      = None   # None = absent OU explicitement null

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> list[str] | None:
        return validate_tags_field(v)

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        size = len(json.dumps(v, separators=(",", ":")))
        if size > PAYLOAD_MAX_BYTES:
            raise ValueError(
                f"payload exceeds 4 KB limit ({size} bytes serialized)"
            )
        return v

    model_config = {"extra": "ignore"}

    def provided_fields(self, raw_data: dict) -> dict:

        allowed = {"kind", "tags", "payload"}
        result = {}
        for k in allowed:
            if k not in raw_data:
                continue
            # Récupère la valeur validée par Pydantic (enum converti, etc.)
            result[k] = getattr(self, k)
        return result


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class EventResponse(BaseModel):
    id:          int
    user_id:     str
    occurred_at: str   # ← occurred_at_raw (valeur originale client)
    created_at:  str   # ← alias de occurred_at, même valeur (spec §3)
    recorded_at: str
    kind:        str
    tags:        list[str]
    payload:     dict | None

    @classmethod
    def from_row(cls, row) -> "EventResponse":

        import json as _json
        payload_raw = row["payload"]
        return cls(
            id          = row["id"],
            user_id     = row["user_id"],
            occurred_at = row["occurred_at_raw"],   # valeur originale
            created_at  = row["occurred_at_raw"],   # alias, même valeur
            recorded_at = row["recorded_at"],
            kind        = row["kind"],
            tags        = _json.loads(row["tags"]),
            payload     = _json.loads(payload_raw) if payload_raw else None,
        )


class EventListResponse(BaseModel):
    event_count:  int
    events:       list[EventResponse]
    next_cursor:  str | None = None


class StatsResponse(BaseModel):
    total_events:       int
    events_by_kind:     dict[str, int]
    median_gap_seconds: float | None
    unique_users:       int