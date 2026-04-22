"""
tests/test_list.py
------------------
GET /events
"""

import pytest
from httpx import AsyncClient
from tests.conftest import make_event


async def _seed(client, events: list[dict]):
    ids = []
    for e in events:
        r = await client.post("/events", json=e)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient):
    r = await client.get("/events")
    assert r.status_code == 200
    data = r.json()
    assert data["event_count"] == 0
    assert data["events"] == []
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_order_desc(client: AsyncClient):
    await _seed(client, [
        make_event(user_id="u1", occurred_at="2026-01-01T00:01:00Z"),
        make_event(user_id="u2", occurred_at="2026-01-01T00:03:00Z"),
        make_event(user_id="u3", occurred_at="2026-01-01T00:02:00Z"),
    ])
    r = await client.get("/events")
    times = [e["occurred_at"] for e in r.json()["events"]]
    assert times == sorted(times, reverse=True)


@pytest.mark.asyncio
async def test_filter_by_user_id(client: AsyncClient):
    await _seed(client, [
        make_event(user_id="alice"),
        make_event(user_id="bob", occurred_at="2026-01-01T00:01:00Z"),
    ])
    r = await client.get("/events?user_id=alice")
    data = r.json()
    assert data["event_count"] == 1
    assert data["events"][0]["user_id"] == "alice"


@pytest.mark.asyncio
async def test_filter_by_kind_multiple(client: AsyncClient):
    await _seed(client, [
        make_event(user_id="u1", kind="click"),
        make_event(user_id="u2", occurred_at="2026-01-01T00:01:00Z", kind="view"),
        make_event(user_id="u3", occurred_at="2026-01-01T00:02:00Z", kind="purchase"),
    ])
    r = await client.get("/events?kind=click&kind=view")
    data = r.json()
    assert data["event_count"] == 2
    kinds = {e["kind"] for e in data["events"]}
    assert kinds == {"click", "view"}


@pytest.mark.asyncio
async def test_filter_by_tag_and_semantics(client: AsyncClient):
    #Plusieurs ?tag= → AND : l'event doit avoir TOUS les tags.
    await _seed(client, [
        make_event(user_id="u1", tags=["a", "b"]),
        make_event(user_id="u2", occurred_at="2026-01-01T00:01:00Z", tags=["a"]),
        make_event(user_id="u3", occurred_at="2026-01-01T00:02:00Z", tags=["b"]),
    ])
    r = await client.get("/events?tag=a&tag=b")
    data = r.json()
    assert data["event_count"] == 1
    assert data["events"][0]["user_id"] == "u1"


@pytest.mark.asyncio
async def test_filter_from_to(client: AsyncClient):
    await _seed(client, [
        make_event(user_id="u1", occurred_at="2026-01-01T00:00:00Z"),
        make_event(user_id="u2", occurred_at="2026-01-01T01:00:00Z"),
        make_event(user_id="u3", occurred_at="2026-01-01T02:00:00Z"),
    ])
    r = await client.get(
        "/events?from=2026-01-01T00:30:00Z&to=2026-01-01T01:30:00Z"
    )
    data = r.json()
    assert data["event_count"] == 1
    assert data["events"][0]["user_id"] == "u2"


@pytest.mark.asyncio
async def test_pagination_cursor(client: AsyncClient):
    """3 events, limit=2 → page 1 a next_cursor, page 2 n'en a pas."""
    await _seed(client, [
        make_event(user_id="u1", occurred_at="2026-01-01T00:01:00Z"),
        make_event(user_id="u2", occurred_at="2026-01-01T00:02:00Z"),
        make_event(user_id="u3", occurred_at="2026-01-01T00:03:00Z"),
    ])

    r1 = await client.get("/events?limit=2")
    data1 = r1.json()
    assert data1["event_count"] == 2
    assert data1["next_cursor"] is not None

    r2 = await client.get(f"/events?limit=2&cursor={data1['next_cursor']}")
    data2 = r2.json()
    assert data2["event_count"] == 1
    assert data2["next_cursor"] is None

    # Pas de doublon entre pages
    ids_p1 = {e["id"] for e in data1["events"]}
    ids_p2 = {e["id"] for e in data2["events"]}
    assert ids_p1.isdisjoint(ids_p2)


@pytest.mark.asyncio
async def test_invalid_cursor_rejected(client: AsyncClient):
    r = await client.get("/events?cursor=notvalidbase64!!!")
    assert r.status_code == 400