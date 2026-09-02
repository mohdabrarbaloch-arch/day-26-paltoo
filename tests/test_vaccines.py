"""Pure-logic tests for the vaccine scheduler."""

from datetime import date, timedelta

import pytest

from app.services import vaccines


class FakePet:
    def __init__(self, species, birth_date, vaccine_records=()):
        self.species = species
        self.birth_date = birth_date
        self.vaccine_records = list(vaccine_records)


class FakeRecord:
    def __init__(self, key, administered_on):
        self.vaccine_key = key
        self.administered_on = administered_on


TODAY = date(2026, 9, 2)
PUPPY_BORN = TODAY - timedelta(days=60)  # ~8.5 weeks
ADULT_BORN = TODAY - timedelta(days=365 * 3)
ADULT_RECORDS = [
    FakeRecord("dhpp", TODAY - timedelta(days=30)),
    FakeRecord("rabies", TODAY - timedelta(days=200)),
]


def test_dog_vaccine_keys_exist():
    keys = vaccines.DOG_VACCINES
    assert "dhpp" in keys and "rabies" in keys and "lepto" in keys


def test_cat_vaccine_keys_exist():
    assert {"fvrp", "rabies", "felv"} <= set(vaccines.CAT_VACCINES)


def test_unknown_vaccine_for_species_raises():
    with pytest.raises(KeyError):
        vaccines.compute_due_date(FakePet("dog", ADULT_BORN), "felv", TODAY - timedelta(days=100))


def test_puppy_starter_dhpp_due_at_6_weeks():
    pet = FakePet("dog", PUPPY_BORN)
    due = vaccines.compute_due_date(pet, "dhpp", None)
    assert due == PUPPY_BORN + timedelta(days=42)


def test_kitten_starter_fvrp_at_8_weeks():
    pet = FakePet("cat", TODAY - timedelta(days=80))
    due = vaccines.compute_due_date(pet, "fvrp", None)
    assert due == (TODAY - timedelta(days=80)) + timedelta(days=56)


def test_rabies_never_before_16_weeks():
    # Even a 10-week-old puppy cannot get an overdue rabies flag before 16 weeks.
    pet = FakePet("dog", TODAY - timedelta(days=70))
    due = vaccines.compute_due_date(pet, "rabies", None)
    assert due >= TODAY - timedelta(days=70) + timedelta(days=112)


def test_booster_is_last_dose_plus_interval():
    pet = FakePet("dog", ADULT_BORN)
    last = TODAY - timedelta(days=300)
    due = vaccines.compute_due_date(pet, "dhpp", last)
    assert due == last + timedelta(days=365)


def test_adult_with_recent_records_is_covered():
    pet = FakePet("dog", ADULT_BORN, vaccine_records=ADULT_RECORDS)
    reminders = vaccines.compute_reminders(pet, today=TODAY)
    by_key = {r.key: r for r in reminders}
    # Core vaccines (dhpp + rabies) are safely covered; only optional extras
    # the adult never received (lepto etc.) show as due/overdue.
    assert by_key["dhpp"].status == "covered"
    assert by_key["rabies"].status == "covered"


def test_missing_dhpp_on_adult_is_overdue():
    pet = FakePet(
        "dog", ADULT_BORN, vaccine_records=[FakeRecord("rabies", TODAY - timedelta(days=200))]
    )
    reminders = vaccines.compute_reminders(pet, today=TODAY)
    by_key = {r.key: r for r in reminders}
    assert by_key["dhpp"].status == "overdue"


def test_upcoming_window_14_days():
    pet = FakePet(
        "dog", ADULT_BORN, vaccine_records=[FakeRecord("rabies", TODAY - timedelta(days=355))]
    )
    reminders = vaccines.compute_reminders(pet, today=TODAY)
    by_key = {r.key: r for r in reminders}
    assert by_key["rabies"].status == "due"


def test_summary_counts_are_consistent():
    pet = FakePet("dog", TODAY - timedelta(days=400))
    reminders = vaccines.compute_reminders(pet, today=TODAY)
    summary = vaccines.summary_counts(reminders)
    assert summary["overdue"] + summary["due"] + summary["upcoming"] + summary["covered"] == len(
        reminders
    )
    assert summary["needs_action"] == summary["overdue"] + summary["due"]


def test_starter_overdue_flag_only_after_6_weeks():
    young = FakePet("dog", TODAY - timedelta(days=30))
    assert vaccines.is_starter_overdue(young, TODAY) is False
    old = FakePet("dog", TODAY - timedelta(days=60))
    assert vaccines.is_starter_overdue(old, TODAY) is True


def test_multiple_doses_uses_latest():
    records = [
        FakeRecord("rabies", TODAY - timedelta(days=500)),
        FakeRecord("rabies", TODAY - timedelta(days=100)),
    ]
    pet = FakePet("cat", ADULT_BORN, vaccine_records=records)
    reminders = vaccines.compute_reminders(pet, today=TODAY)
    by_key = {r.key: r for r in reminders}
    assert by_key["rabies"].due_date == (TODAY - timedelta(days=100)) + timedelta(days=365)
