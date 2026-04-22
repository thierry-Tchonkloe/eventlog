"""
tests/test_timestamps.py
------------------------
"""

import pytest
from httpx import AsyncClient
from tests.conftest import make_event


@pytest.mark.asyncio
async def test_offset_preserved_in_response(client: AsyncClient):

    payload = make_event(occurred_at="2026-04-21T10:30:00-04:00")
    r = await client.post("/events", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["occurred_at"] == "2026-04-21T10:30:00-04:00"
    assert data["created_at"] == "2026-04-21T10:30:00-04:00"


@pytest.mark.asyncio
async def test_created_at_is_alias_of_occurred_at(client: AsyncClient):
    payload = make_event(occurred_at="2026-04-21T14:30:00Z")
    r = await client.post("/events", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["occurred_at"] == data["created_at"]


@pytest.mark.asyncio
async def test_utc_z_format_preserved(client: AsyncClient):
    payload = make_event(occurred_at="2026-04-21T14:30:00Z")
    r = await client.post("/events", json=payload)
    assert r.json()["occurred_at"] == "2026-04-21T14:30:00Z"


@pytest.mark.asyncio
async def test_recorded_at_is_server_time(client: AsyncClient):
    payload = make_event(occurred_at="2020-01-01T00:00:00Z")
    r = await client.post("/events", json=payload)
    data = r.json()
    # recorded_at doit être différent de occurred_at (événement ancien)
    assert data["recorded_at"] != data["occurred_at"]
    # recorded_at doit être une date récente (pas 2020)
    assert data["recorded_at"].startswith("202")  # année courante


@pytest.mark.asyncio
async def test_naive_datetime_rejected(client: AsyncClient):
    payload = make_event(occurred_at="2026-04-21T14:30:00")
    r = await client.post("/events", json=payload)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_invalid_datetime_rejected(client: AsyncClient):
    payload = make_event(occurred_at="not-a-date")
    r = await client.post("/events", json=payload)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_deduplication_uses_utc_equivalence(client: AsyncClient):
    r1 = await client.post("/events", json=make_event(
        occurred_at="2026-04-21T10:30:00-04:00"
    ))
    assert r1.status_code == 201

    r2 = await client.post("/events", json=make_event(
        occurred_at="2026-04-21T14:30:00Z"  # même instant UTC
    ))
    assert r2.status_code == 409
    assert r2.json()["code"] == "duplicate_event"