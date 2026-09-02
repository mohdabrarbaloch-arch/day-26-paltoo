"""Slot engine + double-booking protection tests."""

from datetime import date, timedelta

from app.services import slots


def test_slot_list_shape():
    s = slots.slot_list()
    assert s[0] == "10:00"
    assert s[-1] == "19:30"
    assert len(s) == 20  # 10:00..19:30 inclusive, 30-min steps


def test_window_boundaries():
    assert slots.is_within_window(date.today())
    assert slots.is_within_window(date.today() + timedelta(days=13))
    assert not slots.is_within_window(date.today() - timedelta(days=1))
    assert not slots.is_within_window(date.today() + timedelta(days=15))


def test_booked_slot_not_available(client, db):
    owner = client.post(
        "/api/auth/register",
        json={
            "email": "o1@t.pk",
            "password": "owner1234",
            "name": "Owais",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "owner",
        },
    )
    vet = client.post(
        "/api/auth/register",
        json={
            "email": "v1@t.pk",
            "password": "vet12345",
            "name": "Dr V",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "vet",
        },
    )
    oh = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    vet_id = vet.json()["user"]["id"]

    pet = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Tommy",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-01-01",
            "weight_kg": 5,
        },
    )
    pet_id = pet.json()["id"]

    d = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/api/appointments",
        headers=oh,
        json={
            "vet_id": vet_id,
            "pet_id": pet_id,
            "date": d,
            "slot": "10:00",
            "reason": "Vaccination",
        },
    )
    assert res.status_code == 201

    # Slot now gone
    free = client.get(f"/api/vets/{vet_id}/slots?date={d}").json()["slots"]
    assert "10:00" not in free

    # Same vet+date+slot from a second owner -> 409 double-booking guard
    client.post(
        "/api/auth/register",
        json={
            "email": "o2@t.pk",
            "password": "owner1234",
            "name": "O2",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "owner",
        },
    )
    oh2 = client.post("/api/auth/login", data={"username": "o2@t.pk", "password": "owner1234"})
    oh2 = {"Authorization": f"Bearer {oh2.json()['access_token']}"}
    pet2 = client.post(
        "/api/pets",
        headers=oh2,
        json={
            "name": "Leo",
            "species": "cat",
            "gender": "male",
            "birth_date": "2023-06-01",
            "weight_kg": 4,
        },
    )
    pet2_id = pet2.json()["id"]
    clash = client.post(
        "/api/appointments",
        headers=oh2,
        json={"vet_id": vet_id, "pet_id": pet2_id, "date": d, "slot": "10:00", "reason": "Checkup"},
    )
    assert clash.status_code == 409


def test_second_slot_same_vet_same_day_ok(client, db):
    owner = client.post(
        "/api/auth/register",
        json={
            "email": "a@t.pk",
            "password": "owner1234",
            "name": "Ali",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "owner",
        },
    ).json()
    vet = client.post(
        "/api/auth/register",
        json={
            "email": "b@t.pk",
            "password": "vet12345",
            "name": "Dr B",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "vet",
        },
    ).json()
    oh = {"Authorization": f"Bearer {owner['access_token']}"}
    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Rex",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-02-01",
            "weight_kg": 8,
        },
    ).json()["id"]
    d = (date.today() + timedelta(days=2)).isoformat()
    r1 = client.post(
        "/api/appointments",
        headers=oh,
        json={
            "vet_id": vet["user"]["id"],
            "pet_id": pet_id,
            "date": d,
            "slot": "11:00",
            "reason": "Checkup",
        },
    )
    r2 = client.post(
        "/api/appointments",
        headers=oh,
        json={
            "vet_id": vet["user"]["id"],
            "pet_id": pet_id,
            "date": d,
            "slot": "11:30",
            "reason": "Follow-up",
        },
    )
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["ref"] != r2.json()["ref"]


def test_booking_outside_window_rejected(client, db):
    owner = client.post(
        "/api/auth/register",
        json={
            "email": "c@t.pk",
            "password": "owner1234",
            "name": "Chiragh",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "owner",
        },
    ).json()
    vet = client.post(
        "/api/auth/register",
        json={
            "email": "d@t.pk",
            "password": "vet12345",
            "name": "Dr D",
            "phone": "0300-1234567",
            "city": "Khi",
            "role": "vet",
        },
    ).json()
    oh = {"Authorization": f"Bearer {owner['access_token']}"}
    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Max",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-02-01",
            "weight_kg": 8,
        },
    ).json()["id"]
    far = (date.today() + timedelta(days=30)).isoformat()
    res = client.post(
        "/api/appointments",
        headers=oh,
        json={
            "vet_id": vet["user"]["id"],
            "pet_id": pet_id,
            "date": far,
            "slot": "10:00",
            "reason": "Checkup",
        },
    )
    assert res.status_code == 422
