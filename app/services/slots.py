"""Appointment slot generation and conflict checks.

Clinic hours are 10:00 - 20:00, 30-minute slots (last slot 19:30),
up to booking_days_ahead (14) days in the future.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import APPT_CANCELLED, APPT_LIVE, Appointment

EXCLUDED_STATUSES = (APPT_CANCELLED,)


def slot_list() -> list[str]:
    slots: list[str] = []
    cursor = time(settings.clinic_open_hour, 0)
    close = time(settings.clinic_close_hour, 0)
    while cursor < close:
        slots.append(cursor.strftime("%H:%M"))
        cursor = (
            datetime.combine(date.today(), cursor) + timedelta(minutes=settings.slot_minutes)
        ).time()
    return slots


def booking_window_start() -> date:
    return date.today()


def booking_window_end() -> date:
    return date.today() + timedelta(days=settings.booking_days_ahead)


def is_within_window(d: date) -> bool:
    return booking_window_start() <= d <= booking_window_end()


def slot_datetime(d: date, slot: str) -> datetime:
    hour, minute = (int(x) for x in slot.split(":"))
    return datetime.combine(d, time(hour, minute))


def _load_slots_for(db: Session, vet_id: int, d: date) -> set[str]:
    rows = (
        db.execute(
            select(Appointment.slot).where(
                Appointment.vet_id == vet_id,
                Appointment.date == d,
                Appointment.status.in_(APPT_LIVE),
            )
        )
        .scalars()
        .all()
    )
    return set(rows)


def available_slots(db: Session, vet_id: int, d: date) -> list[str]:
    if not is_within_window(d):
        return []
    taken = _load_slots_for(db, vet_id, d)
    return [s for s in slot_list() if s not in taken]


def is_slot_available(db: Session, vet_id: int, d: date, slot: str) -> bool:
    if slot not in slot_list() or not is_within_window(d):
        return False
    return slot not in _load_slots_for(db, vet_id, d)
