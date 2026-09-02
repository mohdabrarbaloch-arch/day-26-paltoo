"""Vaccine-log + vet-appointment lifecycle tests."""

from datetime import date, timedelta

from tests.conftest import auth_headers, make_owner, make_vet, register


TODAY = date.today()


def _setup_booked(client):
    """Owner + verified vet + pet + a confirmed appointment tomorrow 10:00."""
    oh = make_owner(client, email="ownerf@test.pk")
    make_vet(client)
    vh = auth_headers(client, "vet@test.pk", "vet12345")
    vet_id = client.get("/api/auth/me", headers=vh).json()["id"]

    # vet profile is unverified by default -> force-verify via admin
    register(client, email="adminf@test.pk", password="admin12345", role="admin")
    ah = auth_headers(client, "adminf@test.pk", "admin12345")
    profiles = client.get("/api/admin/vets", headers=ah).json()
    profile = next(p for p in profiles if p["user_id"] == vet_id)
    client.post(f"/api/admin/vets/{profile['id']}/verify", headers=ah)

    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Bella",
            "species": "cat",
            "gender": "female",
            "birth_date": "2023-03-10",
            "weight_kg": 3.5,
        },
    ).json()["id"]
    d = (TODAY + timedelta(days=1)).isoformat()
    appt = client.post(
        "/api/appointments",
        headers=oh,
        json={
            "vet_id": vet_id,
            "pet_id": pet_id,
            "date": d,
            "slot": "10:00",
            "reason": "Annual checkup",
        },
    )
    return client, oh, vh, vet_id, pet_id, d, appt


def test_register_and_login_roundtrip(client, db):
    register(client, email="rt@test.pk", name="Rana", city="Multan")
    res = client.post(
        "/api/auth/login", data={"username": "rt@test.pk", "password": "owner1234"}
    )
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


def test_pet_detail_shows_reminders(client, db):
    oh = make_owner(client, email="r1@test.pk")
    # unvaccinated 2-year-old dog
    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Bruno",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-08-01",
            "weight_kg": 12,
        },
    ).json()["id"]
    detail = client.get(f"/api/pets/{pet_id}", headers=oh).json()
    assert detail["reminder_summary"]["needs_action"] > 0
    assert any(r["status"] == "overdue" for r in detail["reminders"])


def test_log_vaccine_shifts_reminder(client, db):
    oh = make_owner(client, email="r2@test.pk")
    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Kalu",
            "species": "dog",
            "gender": "male",
            "birth_date": "2024-09-01",
            "weight_kg": 9,
        },
    ).json()["id"]
    before = client.get(f"/api/pets/{pet_id}", headers=oh).json()
    dhpp_before = next(r for r in before["reminders"] if r["key"] == "dhpp")
    assert dhpp_before["status"] in ("overdue", "due")

    res = client.post(
        f"/api/pets/{pet_id}/vaccines",
        headers=oh,
        json={"vaccine_key": "dhpp", "administered_on": TODAY.isoformat()},
    )
    assert res.status_code == 201
    assert res.json()["vaccine_name"].startswith("DHPP")

    after = client.get(f"/api/pets/{pet_id}", headers=oh).json()
    dhpp_after = next(r for r in after["reminders"] if r["key"] == "dhpp")
    assert dhpp_after["status"] == "covered"
    assert dhpp_after["due_date"] == TODAY + timedelta(days=365)


def test_log_vaccine_unknown_key_rejected(client, db):
    oh = make_owner(client, email="r3@test.pk")
    pet_id = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Coco",
            "species": "cat",
            "gender": "female",
            "birth_date": "2023-01-01",
            "weight_kg": 4,
        },
    ).json()["id"]
    # felv is not in the dog schedule -> but Coco is a cat, so use a dog key
    bad_pet = client.post(
        "/api/pets",
        headers=oh,
        json={
            "name": "Pluto",
            "species": "dog",
            "gender": "male",
            "birth_date": "2023-01-01",
            "weight_kg": 8,
        },
    ).json()["id"]
    res = client.post(
        f"/api/pets/{bad_pet}/vaccines",
        headers=oh,
        json={"vaccine_key": "felv", "administered_on": TODAY.isoformat()},
    )
    assert res.status_code == 422


def test_vet_sees_only_own_appointments(client, db):
    client, oh, vh, vet_id, pet_id, d, appt = _setup_booked(client)
    day = client.get("/api/me/vet/appointments", headers=vh).json()
    assert len(day) >= 1
    assert all(a["vet"]["id"] == vet_id for a in day)


def test_vet_confirms_then_completes(client, db):
    client, oh, vh, vet_id, pet_id, d, appt = _setup_booked(client)
    appt_id = appt.json()["id"]

    # confirmed -> completed is legal
    res = client.post(
        f"/api/me/vet/appointments/{appt_id}/status?new_status=completed", headers=vh
    )
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

    # completed -> no_show is illegal
    res2 = client.post(
        f"/api/me/vet/appointments/{appt_id}/status?new_status=no_show", headers=vh
    )
    assert res2.status_code == 409


def test_vet_cannot_touch_other_vets_appointment(client, db):
    client, oh, vh, vet_id, pet_id, d, appt = _setup_booked(client)
    appt_id = appt.json()["id"]
    # second vet
    register(client, email="vet2@test.pk", password="vet12345", role="vet")
    vh2 = auth_headers(client, "vet2@test.pk", "vet12345")
    res = client.post(
        f"/api/me/vet/appointments/{appt_id}/status?new_status=completed", headers=vh2
    )
    assert res.status_code == 404


def test_cancel_frees_slot(client, db):
    client, oh, vh, vet_id, pet_id, d, appt = _setup_booked(client)
    appt_id = appt.json()["id"]
    assert "10:00" not in client.get(f"/api/vets/{vet_id}/slots?date={d}").json()["slots"]

    res = client.post(f"/api/appointments/{appt_id}/cancel", headers=oh)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"
    assert "10:00" in client.get(f"/api/vets/{vet_id}/slots?date={d}").json()["slots"]


def test_appointment_has_sequential_ref(client, db):
    client, oh, vh, vet_id, pet_id, d, appt = _setup_booked(client)
    ref = appt.json()["ref"]
    assert ref.startswith("PLT-")
    assert ref.endswith("-000001") or ref.endswith("-000002") or ref.endswith("-000003")


def test_vet_profile_patch_updates_fee(client, db):
    register(client, email="v3@test.pk", password="vet12345", role="vet")
    vh = auth_headers(client, "v3@test.pk", "vet12345")
    res = client.patch("/api/me/vet-profile", headers=vh, json={"fee_pkr": 3500})
    assert res.status_code == 200
    assert res.json()["fee_pkr"] == 3500


def test_public_stats_shape(client, db):
    stats = client.get("/api/stats").json()
    for key in ("vets", "verified_vets", "pets", "appointments_total", "appointments_today", "cities"):
        assert key in stats
