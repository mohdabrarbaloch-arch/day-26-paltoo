"""Auth + scoping tests: registration rules, role guards, 404-on-foreign."""

import pytest

from tests.conftest import auth_headers, make_admin, make_owner, make_vet, register


def test_register_owner_succeeds(client, db):
    res = register(client, email="ali@test.pk", name="Ali", city="Lahore", role="owner")
    assert res.status_code == 201
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "owner"


def test_register_duplicate_email_conflict(client, db):
    register(client, email="dup@test.pk")
    res = register(client, email="dup@test.pk")
    assert res.status_code == 409


def test_register_weak_password_rejected(client, db):
    res = register(client, email="weak@test.pk", password="short")
    assert res.status_code == 422


def test_register_invalid_role_rejected(client, db):
    res = register(client, email="bad@test.pk", role="superuser")
    assert res.status_code == 422


def test_register_creates_vet_profile_for_vet_role(client, db):
    res = register(client, email="vet1@test.pk", password="vet12345", role="vet")
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "vet"
    # profile is created but unverified -> not in public directory yet
    public = client.get("/api/vets").json()
    assert all(v["user_id"] != res.json()["user"]["id"] for v in public)


def test_login_wrong_password(client, db):
    register(client, email="login@test.pk")
    res = client.post("/api/auth/login", data={"username": "login@test.pk", "password": "wrong1234"})
    assert res.status_code == 401


def test_me_requires_token(client, db):
    assert client.get("/api/auth/me").status_code == 401


def test_vet_cannot_create_pets(client, db):
    make_vet(client)
    vh = auth_headers(client, "vet@test.pk", "vet12345")
    res = client.post(
        "/api/pets",
        headers=vh,
        json={
            "name": "Shero",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-05-05",
            "weight_kg": 10,
        },
    )
    assert res.status_code == 403


def test_owner_cannot_see_other_owner_pet(client, db):
    oh1 = make_owner(client, email="o1@test.pk")
    pet = client.post(
        "/api/pets",
        headers=oh1,
        json={
            "name": "Tommy",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-01-01",
            "weight_kg": 5,
        },
    )
    pet_id = pet.json()["id"]
    oh2 = make_owner(client, email="o2@test.pk")
    # Foreign pet -> 404 (no existence leak)
    assert client.get(f"/api/pets/{pet_id}", headers=oh2).status_code == 404
    # Owner sees own pet fine
    assert client.get(f"/api/pets/{pet_id}", headers=oh1).status_code == 200


def test_owner_cannot_cancel_others_appointment(client, db):
    oh1 = make_owner(client, email="x1@test.pk")
    vh = make_vet(client)
    vet_id = client.get("/api/auth/me", headers=vh).json()["id"]
    pet_id = client.post(
        "/api/pets",
        headers=oh1,
        json={
            "name": "Milo",
            "species": "cat",
            "gender": "male",
            "birth_date": "2023-01-01",
            "weight_kg": 4,
        },
    ).json()["id"]
    from datetime import date, timedelta

    d = (date.today() + timedelta(days=1)).isoformat()
    appt = client.post(
        "/api/appointments",
        headers=oh1,
        json={
            "vet_id": vet_id,
            "pet_id": pet_id,
            "date": d,
            "slot": "10:00",
            "reason": "Vaccination",
        },
    )
    appt_id = appt.json()["id"]
    oh2 = make_owner(client, email="x2@test.pk")
    res = client.post(f"/api/appointments/{appt_id}/cancel", headers=oh2)
    assert res.status_code == 404


def test_admin_verify_flow(client, db):
    register(client, email="v@test.pk", password="vet12345", role="vet")
    vh = auth_headers(client, "v@test.pk", "vet12345")
    me = client.get("/api/auth/me", headers=vh).json()
    # Vet not in public directory yet
    assert client.get("/api/vets").json() == []
    # Vet cannot verify self
    assert client.get("/api/admin/vets", headers=vh).status_code == 403

    ah = make_admin(client)
    profiles = client.get("/api/admin/vets", headers=ah).json()
    assert len(profiles) == 1
    pid = profiles[0]["id"]
    res = client.post(f"/api/admin/vets/{pid}/verify", headers=ah)
    assert res.status_code == 200
    assert res.json()["verified"] is True
    # Now in public directory
    public = client.get("/api/vets").json()
    assert any(v["id"] == pid for v in public)


def test_rate_limiter_active(client, db):
    # 11 rapid login attempts -> the 11th should trip the 10/min login limit
    register(client, email="rl@test.pk")
    codes = []
    for _ in range(11):
        res = client.post(
            "/api/auth/login", data={"username": "rl@test.pk", "password": "wrong1234"}
        )
        codes.append(res.status_code)
    assert 429 in codes
