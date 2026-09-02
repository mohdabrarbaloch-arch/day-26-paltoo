"""Appointment booking, listing and cancellation.

Booking is double-booking-safe: the free-slot check and the insert happen in a
single transaction that re-checks inside the database, and the appointment ref
is unique, so two concurrent requests for the same slot cannot both succeed.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import APPT_CONFIRMED, APPT_LIVE, ROLE_OWNER, ROLE_VET, Appointment, Pet, User, utcnow
from ..schemas import AppointmentCreate, AppointmentOut
from ..security import get_current_user
from ..services import slots

router = APIRouter(prefix="/api", tags=["appointments"])

_APPT_OPTIONS = (selectinload(Appointment.vet), selectinload(Appointment.pet))


def _load_appointment(db: Session, appt_id: int) -> Appointment | None:
    return db.scalar(select(Appointment).where(Appointment.id == appt_id).options(*_APPT_OPTIONS))


def _next_ref(db: Session) -> str:
    year = utcnow().year
    prefix = f"PLT-{year}-"
    last = db.scalar(
        select(Appointment.ref)
        .where(Appointment.ref.like(f"{prefix}%"))
        .order_by(Appointment.ref.desc())
        .limit(1)
    )
    seq = int(last.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:06d}"


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner books a slot with a vet for one of their pets."""
    if user.role != ROLE_OWNER:
        raise HTTPException(status_code=403, detail="Only pet owners can book appointments")

    pet = db.get(Pet, payload.pet_id)
    if pet is None or pet.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Pet not found")

    vet = db.get(User, payload.vet_id)
    if vet is None or vet.role != ROLE_VET or not vet.is_active:
        raise HTTPException(status_code=404, detail="Vet not found")

    if not slots.is_within_window(payload.date):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Bookings open {slots.booking_window_start()} to "
                f"{slots.booking_window_end()} only"
            ),
        )
    if payload.slot not in slots.slot_list():
        raise HTTPException(status_code=422, detail="Invalid slot")

    # Atomic check-and-insert inside one transaction. The unique ref plus the
    # re-check below means a concurrent request for the same slot loses cleanly.
    if not slots.is_slot_available(db, vet.id, payload.date, payload.slot):
        raise HTTPException(
            status_code=409, detail="That slot was just booked — please pick another"
        )

    appointment = Appointment(
        ref=_next_ref(db),
        pet_id=pet.id,
        vet_id=vet.id,
        owner_id=user.id,
        date=payload.date,
        slot=payload.slot,
        reason=payload.reason,
        status=APPT_CONFIRMED,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return _load_appointment(db, appointment.id)


@router.get("/appointments", response_model=list[AppointmentOut])
def my_appointments(
    upcoming_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner sees their pets' appointments; vet sees their own calendar."""
    if user.role == ROLE_VET:
        query = select(Appointment).where(Appointment.vet_id == user.id)
    elif user.role == ROLE_OWNER:
        query = select(Appointment).where(Appointment.owner_id == user.id)
    else:
        raise HTTPException(status_code=403, detail="Admins manage via other views")
    query = query.options(*_APPT_OPTIONS).order_by(Appointment.date, Appointment.slot)
    if upcoming_only:
        query = query.where(Appointment.date >= utcnow().date())
    return [a for a in db.scalars(query).all()]


@router.get("/appointments/{appt_id}", response_model=AppointmentOut)
def appointment_detail(
    appt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appt = _load_appointment(db, appt_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if user.role not in (ROLE_OWNER, ROLE_VET) or not (
        appt.owner_id == user.id or appt.vet_id == user.id
    ):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/appointments/{appt_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner cancels their own appointment (slot frees up instantly)."""
    appt = _load_appointment(db, appt_id)
    if appt is None or appt.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status not in APPT_LIVE:
        raise HTTPException(status_code=409, detail="This appointment can no longer be cancelled")
    appt.status = "cancelled"
    db.commit()
    db.refresh(appt)
    return _load_appointment(db, appt.id)
