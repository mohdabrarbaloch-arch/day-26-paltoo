"""Vaccination schedules and reminder logic for pets.

Vaccines use species-appropriate core schedules plus optional extras.
Reminder dates are computed from a pet's age (puppy/kitten series) or the
last administered dose (boosters), whichever is later.

All intervals are in days.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

# Core + common optional vaccines per species.
# key: machine name, name: display name, interval_days: revaccination interval
DOG_VACCINES: dict[str, dict] = {
    "dhpp": {"name": "DHPP (Distemper, Hepatitis, Parvo)", "interval_days": 365},
    "rabies": {"name": "Rabies", "interval_days": 365},
    "lepto": {"name": "Leptospirosis", "interval_days": 365},
    "bordetella": {"name": "Bordetella (kennel cough)", "interval_days": 180},
    "heartworm": {"name": "Heartworm prevention", "interval_days": 30},
}
CAT_VACCINES: dict[str, dict] = {
    "fvrp": {"name": "FVRCP (Feline distemper)", "interval_days": 365},
    "rabies": {"name": "Rabies", "interval_days": 365},
    "felv": {"name": "FeLV (Feline leukemia)", "interval_days": 365},
}
OTHER_VACCINES: dict[str, dict] = {
    "rabies": {"name": "Rabies", "interval_days": 365},
}

# First-dose ages in days for the puppy/kitten starter series
STARTER_DOG_DAYS = 42  # ~6 weeks
STARTER_CAT_DAYS = 56  # ~8 weeks


def vaccines_for_species(species: str) -> dict[str, dict]:
    if species == "dog":
        return DOG_VACCINES
    if species == "cat":
        return CAT_VACCINES
    return OTHER_VACCINES


def age_days(pet: object, today: date | None = None) -> int:
    today = today or date.today()
    return (today - pet.birth_date).days


def is_starter_overdue(pet: object, today: date | None = None) -> bool:
    """True if a puppy/kitten has not yet had any vaccination record."""
    today = today or date.today()
    threshold = STARTER_DOG_DAYS if pet.species == "dog" else STARTER_CAT_DAYS
    return age_days(pet, today) > threshold and not pet.vaccine_records


def _last_dose_date(records: list, key: str) -> date | None:
    doses = [r for r in records if r.vaccine_key == key]
    return max((r.administered_on for r in doses), default=None)


def compute_due_date(pet: object, key: str, last_dose: date | None = None) -> date:
    """Next due date for a vaccine: starter schedule (if never dosed) else
    last dose + interval. For rabies the first dose is legally required at
    16 weeks in most regions; we use the species starter rule otherwise.
    """
    vac = vaccines_for_species(pet.species).get(key)
    if vac is None:
        raise KeyError(f"vaccine '{key}' not available for {pet.species}")
    if last_dose is None:
        starter = STARTER_DOG_DAYS if pet.species == "dog" else STARTER_CAT_DAYS
        if key == "rabies":
            starter = max(starter, 112)  # 16 weeks
        return pet.birth_date + timedelta(days=starter)
    return last_dose + timedelta(days=vac["interval_days"])


@dataclass
class Reminder:
    key: str
    name: str
    due_date: date
    days_left: int
    status: str = field(default="", init=False)

    def __post_init__(self):
        if self.days_left < 0:
            self.status = "overdue"
        elif self.days_left <= 14:
            self.status = "due"
        elif self.days_left <= 30:
            self.status = "upcoming"
        else:
            self.status = "covered"


def compute_reminders(
    pet: object,
    last_doses: dict[str, date] | None = None,
    today: date | None = None,
) -> list[Reminder]:
    """Compute reminder status for every vaccine in the pet's schedule."""
    today = today or date.today()
    doses = (
        last_doses
        if last_doses is not None
        else {r.vaccine_key: r.administered_on for r in pet.vaccine_records}
    )
    out: list[Reminder] = []
    for key, meta in vaccines_for_species(pet.species).items():
        last = doses.get(key)
        due = compute_due_date(pet, key, last)
        days_left = (due - today).days
        out.append(Reminder(key=key, name=meta["name"], due_date=due, days_left=days_left))
    out.sort(key=lambda r: r.days_left)
    return out


def summary_counts(reminders: list[Reminder]) -> dict:
    counts = {"overdue": 0, "due": 0, "upcoming": 0, "covered": 0}
    for r in reminders:
        counts[r.status] += 1
    counts["needs_action"] = counts["overdue"] + counts["due"]
    return counts


def vaccine_key_options(species: str) -> list[dict]:
    return [
        {"key": k, "name": v["name"], "interval_days": v["interval_days"]}
        for k, v in vaccines_for_species(species).items()
    ]
