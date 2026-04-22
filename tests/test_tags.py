"""
tests/test_tags.py
------------------
"""

import pytest
from httpx import AsyncClient
from tests.conftest import make_event


@pytest.mark.asyncio
async def test_tags_absent_is_ok(client: AsyncClient):
    r = await client.post("/events", json=make_event())
    assert r.status_code == 201
    assert r.json()["tags"] == []


@pytest.mark.asyncio
async def test_tags_empty_array_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags=[]))
    assert r.status_code == 400
    assert "empty" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_tags_bare_string_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags="foo"))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tags_valid(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags=["checkout", "promo-2026"]))
    assert r.status_code == 201
    assert set(r.json()["tags"]) == {"checkout", "promo-2026"}


@pytest.mark.asyncio
async def test_tags_uppercase_rejected(client: AsyncClient):
    """Tags doivent être lowercase uniquement."""
    r = await client.post("/events", json=make_event(tags=["Checkout"]))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tags_special_chars_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags=["hello world"]))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tags_too_long_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags=["a" * 33]))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_tags_duplicates_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(tags=["foo", "bar", "foo"]))
    assert r.status_code == 400
    assert "duplicate" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_tags_max_16(client: AsyncClient):
    tags = [f"tag-{i:02d}" for i in range(16)]
    r = await client.post("/events", json=make_event(tags=tags))
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_tags_17_rejected(client: AsyncClient):
    tags = [f"tag-{i:02d}" for i in range(17)]
    r = await client.post("/events", json=make_event(tags=tags))
    assert r.status_code == 400