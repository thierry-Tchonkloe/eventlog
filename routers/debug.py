"""
routers/debug.py
----------------
POST /debug/echo — spec §7

"""

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from typing import Any

router = APIRouter(tags=["debug"])


def _transform(value, *, parent_key: str | None = None):

    if isinstance(value, str):
        if parent_key == "preserve":
            return value
        return value[::-1]  # inversion Python, O(n), lisible

    if isinstance(value, dict):
        return {
            k: _transform(v, parent_key=k)
            for k, v in value.items()
        }

    if isinstance(value, list):
        # Dans un tableau, les strings n'ont pas de clé parent → elles sont toutes inversées (aucune n'est "preserve")
        return [_transform(item, parent_key=None) for item in value]

    return value # int, float, bool, None → passthrough


@router.post("/debug/echo")
async def debug_echo(payload: Any = Body(...)):
    return JSONResponse(_transform(payload))