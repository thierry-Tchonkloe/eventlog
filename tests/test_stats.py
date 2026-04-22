"""
tests/test_stats.py
-------------------
"""

import pytest
from httpx import AsyncClient
from tests.conftest import make_event


@pytest.mark.asyncio
async def test_stats_empty_db(client: AsyncClient):
    r = await client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_events"] == 0
    assert data["events_by_kind"] == {}
    assert data["median_gap_seconds"] is None
    assert data["unique_users"] == 0


@pytest.mark.asyncio
async def test_stats_single_event(client: AsyncClient):
    await client.post("/events", json=make_event())
    r = await client.get("/stats")
    data = r.json()
    assert data["total_events"] == 1
    assert data["median_gap_seconds"] is None


@pytest.mark.asyncio
async def test_stats_two_events_gap(client: AsyncClient):
    await client.post("/events", json=make_event(
        user_id="alice", occurred_at="2026-01-01T00:00:00Z"
    ))
    await client.post("/events", json=make_event(
        user_id="bob", occurred_at="2026-01-01T00:01:00Z"  # +60s
    ))
    r = await client.get("/stats")
    data = r.json()
    assert data["total_events"] == 2
    assert data["median_gap_seconds"] == 60.0


@pytest.mark.asyncio
async def test_stats_median_odd(client: AsyncClient):
    events = [
        make_event(user_id="u1", occurred_at="2026-01-01T00:00:00Z"),
        make_event(user_id="u2", occurred_at="2026-01-01T00:01:00Z"),  # gap: 60s
        make_event(user_id="u3", occurred_at="2026-01-01T00:04:00Z"),  # gap: 180s
    ]
    for e in events:
        await client.post("/events", json=e)

    r = await client.get("/stats")
    assert r.json()["median_gap_seconds"] == 120.0


@pytest.mark.asyncio
async def test_stats_events_by_kind(client: AsyncClient):
    await client.post("/events", json=make_event(kind="click"))
    await client.post("/events", json=make_event(
        user_id="bob", occurred_at="2026-01-01T00:01:00Z", kind="view"
    ))
    await client.post("/events", json=make_event(
        user_id="bob", occurred_at="2026-01-01T00:02:00Z", kind="view"
    ))
    r = await client.get("/stats")
    data = r.json()
    assert data["events_by_kind"]["click"] == 1
    assert data["events_by_kind"]["view"] == 2


@pytest.mark.asyncio
async def test_stats_unique_users(client: AsyncClient):
    await client.post("/events", json=make_event(user_id="alice"))
    await client.post("/events", json=make_event(
        user_id="alice", occurred_at="2026-01-01T00:01:00Z"
    ))
    await client.post("/events", json=make_event(
        user_id="bob", occurred_at="2026-01-01T00:02:00Z"
    ))
    r = await client.get("/stats")
    assert r.json()["unique_users"] == 2