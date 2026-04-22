"""
routers/stats.py
"""
from typing import Annotated
from fastapi import APIRouter, Depends
import aiosqlite
from database import get_db
from models import StatsResponse
from services import stats_service

router = APIRouter(tags=["stats"])

DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: DbDep):
    return await stats_service.get_stats(db)