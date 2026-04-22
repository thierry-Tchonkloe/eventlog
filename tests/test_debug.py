"""
tests/test_debug.py
-------------------
POST /debug/echo
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_echo_basic_reversal(client: AsyncClient):
    r = await client.post("/debug/echo", json={"name": "alice", "age": 30, "preserve": "keepme"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "ecila"
    assert data["age"] == 30           # int → passthrough
    assert data["preserve"] == "keepme"  # clé preserve → inchangé


@pytest.mark.asyncio
async def test_echo_array_reversal(client: AsyncClient):
    r = await client.post("/debug/echo", json={"items": ["foo", "bar"], "preserve": "ok"})
    data = r.json()
    assert data["items"] == ["oof", "rab"]
    assert data["preserve"] == "ok"


@pytest.mark.asyncio
async def test_echo_nested_object(client: AsyncClient):
    r = await client.post("/debug/echo", json={"nested": {"x": "hello", "preserve": "hi"}})
    data = r.json()
    assert data["nested"]["x"] == "olleh"
    assert data["nested"]["preserve"] == "hi"   # preserve local au niveau imbriqué


@pytest.mark.asyncio
async def test_echo_non_string_passthrough(client: AsyncClient):
    r = await client.post("/debug/echo", json={
        "n": 42, "f": 3.14, "b": True, "null_val": None
    })
    data = r.json()
    assert data["n"] == 42
    assert data["f"] == 3.14
    assert data["b"] is True
    assert data["null_val"] is None


@pytest.mark.asyncio
async def test_echo_preserve_deep_nesting(client: AsyncClient):
    r = await client.post("/debug/echo", json={
        "a": {
            "b": {
                "preserve": "deep",
                "name": "test"
            }
        }
    })
    data = r.json()
    assert data["a"]["b"]["preserve"] == "deep"
    assert data["a"]["b"]["name"] == "tset"


@pytest.mark.asyncio
async def test_echo_empty_object(client: AsyncClient):
    r = await client.post("/debug/echo", json={})
    assert r.json() == {}


@pytest.mark.asyncio
async def test_echo_strings_in_array_no_preserve(client: AsyncClient):
    r = await client.post("/debug/echo", json={"list": ["abc", "xyz"]})
    data = r.json()
    assert data["list"] == ["cba", "zyx"]