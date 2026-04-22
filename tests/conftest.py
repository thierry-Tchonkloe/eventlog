"""
tests/conftest.py
-----------------
"""

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

# On importe app APRÈS avoir configuré pytest-asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from database import init_db, get_db, SCHEMA


# Mode auto : tous les tests async sont reconnus sans décorateur
pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.executescript(SCHEMA)
        await conn.commit()
        yield conn


@pytest_asyncio.fixture
async def client(db):
    # Override de la dépendance FastAPI
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    # Nettoyage de l'override après le test
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factories utilitaires (évite la duplication dans les tests)
# ---------------------------------------------------------------------------

def make_event(**kwargs) -> dict:
    base = {
        "user_id": "alice",
        "occurred_at": "2026-04-21T14:30:00Z",
        "kind": "click",
    }
    base.update(kwargs)
    return base