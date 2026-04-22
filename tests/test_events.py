"""
tests/test_events.py
--------------------
Tests CRUD complets
"""

import pytest
from httpx import AsyncClient
from tests.conftest import make_event


# ---------------------------------------------------------------------------
# POST /events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_event_minimal(client: AsyncClient):
    r = await client.post("/events", json=make_event())
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["user_id"] == "alice"
    assert data["kind"] == "click"


@pytest.mark.asyncio
async def test_create_event_full(client: AsyncClient):
    payload = make_event(
        tags=["checkout"],
        payload={"cart_id": 42, "amount": 19.99},
    )
    r = await client.post("/events", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["tags"] == ["checkout"]
    assert data["payload"]["amount"] == 19.99


@pytest.mark.asyncio
async def test_create_event_invalid_kind(client: AsyncClient):
    r = await client.post("/events", json=make_event(kind="unknown"))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_event_invalid_user_id(client: AsyncClient):
    r = await client.post("/events", json=make_event(user_id="alice@bad!"))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_event_user_id_too_long(client: AsyncClient):
    r = await client.post("/events", json=make_event(user_id="a" * 65))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_event_409(client: AsyncClient):
    ev = make_event()
    r1 = await client.post("/events", json=ev)
    assert r1.status_code == 201
    r2 = await client.post("/events", json=ev)
    assert r2.status_code == 409
    assert r2.json()["code"] == "duplicate_event"


@pytest.mark.asyncio
async def test_payload_too_large(client: AsyncClient):
    big = {"data": "x" * (4 * 1024 + 1)}
    r = await client.post("/events", json=make_event(payload=big))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_payload_string_rejected(client: AsyncClient):
    r = await client.post("/events", json=make_event(payload="not_an_object"))  # type: ignore
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /events/<id>
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_event(client: AsyncClient):
    created = (await client.post("/events", json=make_event())).json()
    r = await client.get(f"/events/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    r = await client.get("/events/999999")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# PATCH /events/<id>
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_kind(client: AsyncClient):
    ev = (await client.post("/events", json=make_event())).json()
    r = await client.patch(f"/events/{ev['id']}", json={"kind": "view"})
    assert r.status_code == 200
    assert r.json()["kind"] == "view"


@pytest.mark.asyncio
async def test_patch_not_found(client: AsyncClient):
    r = await client.patch("/events/999999", json={"kind": "view"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_immutable_fields_ignored(client: AsyncClient):
    ev = (await client.post("/events", json=make_event())).json()
    r = await client.patch(
        f"/events/{ev['id']}",
        json={"user_id": "hacker", "occurred_at": "2000-01-01T00:00:00Z"}
    )
    # Doit réussir (les champs inconnus sont ignorés par model_config extra=ignore)
    assert r.status_code == 200
    assert r.json()["user_id"] == "alice"   # inchangé


# ---------------------------------------------------------------------------
# DELETE /events/<id>
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_event(client: AsyncClient):
    ev = (await client.post("/events", json=make_event())).json()
    r = await client.delete(f"/events/{ev['id']}")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient):
    r = await client.delete("/events/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_already_deleted_is_404(client: AsyncClient):
    ev = (await client.post("/events", json=make_event())).json()
    r1 = await client.delete(f"/events/{ev['id']}")
    assert r1.status_code == 204
    r2 = await client.delete(f"/events/{ev['id']}")
    assert r2.status_code == 404