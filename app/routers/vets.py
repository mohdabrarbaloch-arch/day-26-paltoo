"""Vet-related routes: directory, profiles, availability, stats."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import ROLE_VET, Appointment, Pet, User, VetProfile, utcnow
from ..schemas import (
    AppointmentOut,
    AvailableSlotsOut,
    StatsOut,
    VetProfileCreate,
    VetProfileOut,
    VetProfileUpdate,
)
from ..security import require_roles
from ..services import slots

router = APIRouter(prefix="/api", tags=["vets"])


def _profile_with_owner(db: Session, vet_user: User) -> VetProfile:
    profile = db.scalar(
        select(VetProfile)
        .where(VetProfile.user_id == vet_user.id)
        .options(selectinload(VetProfile.user))
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Vet profile not found")
    return profile


# ---------- Public directory ----------


@router.get("/vets", response_model=list[VetProfileOut])
def list_vets(
    city: str | None = None,
    specialty: str | None = None,
    db: Session = Depends(get_db),
):
    """Public vet directory. Non-verified vets are excluded until verified."""
    query = (
        select(VetProfile)
        .join(User, User.id == VetProfile.user_id)
        .where(User.is_active.is_(True), VetProfile.verified.is_(True))
        .options(selectinload(VetProfile.user))
        .order_by(User.created_at.desc())
    )
    if city:
        query = query.where(User.city.ilike(f"%{city}%"))
    if specialty:
        query = query.where(VetProfile.specialty.ilike(f"%{specialty}%"))
    return db.scalars(query).all()


@router.get("/vets/{vet_id}", response_model=VetProfileOut)
def get_vet(vet_id: int, db: Session = Depends(get_db)):
    vet = db.get(User, vet_id)
    if vet is None or vet.role != ROLE_VET or not vet.is_active:
        raise HTTPException(status_code=404, detail="Vet not found")
    profile = _profile_with_owner(db, vet)
    return profile


# ---------- Availability (public) ----------


@router.get("/vets/{vet_id}/slots", response_model=AvailableSlotsOut)
def get_available_slots(vet_id: int, date: date, db: Session = Depends(get_db)):
    """Public: which 30-minute slots are still free for a vet on a date."""
    vet = db.get(User, vet_id)
    if vet is None or vet.role != ROLE_VET or not vet.is_active:
        raise HTTPException(status_code=404, detail="Vet not found")
    return AvailableSlotsOut(date=date, slots=slots.available_slots(db, vet_id, date))


# ---------- Vet self-service ----------


@router.get("/me/vet-profile", response_model=VetProfileOut)
def my_vet_profile(user: User = Depends(require_roles(ROLE_VET)), db: Session = Depends(get_db)):
    return _profile_with_owner(db, user)


@router.post("/me/vet-profile", response_model=VetProfileOut)
def create_vet_profile(
    payload: VetProfileCreate,
    user: User = Depends(require_roles(ROLE_VET)),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(VetProfile).where(VetProfile.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")
    profile = VetProfile(user_id=user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_with_owner(db, user)


@router.patch("/me/vet-profile", response_model=VetProfileOut)
def update_vet_profile(
    payload: VetProfileUpdate,
    user: User = Depends(require_roles(ROLE_VET)),
    db: Session = Depends(get_db),
):
    profile = _profile_with_owner(db, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return _profile_with_owner(db, user)


# ---------- Vet appointment views ----------


@router.get("/me/vet/appointments", response_model=list[AppointmentOut])
def vet_appointments(
    date: date | None = None,
    status: str | None = None,
    user: User = Depends(require_roles(ROLE_VET)),
    db: Session = Depends(get_db),
):
    query = (
        select(Appointment)
        .where(Appointment.vet_id == user.id)
        .options(
            selectinload(Appointment.vet),
            selectinload(Appointment.pet),
        )
        .order_by(Appointment.date, Appointment.slot)
    )
    if date:
        query = query.where(Appointment.date == date)
    if status:
        query = query.where(Appointment.status == status)
    return db.scalars(query).all()


@router.post("/me/vet/appointments/{appt_id}/status", response_model=AppointmentOut)
def update_appointment_status(
    appt_id: int,
    new_status: str,
    user: User = Depends(require_roles(ROLE_VET)),
    db: Session = Depends(get_db),
):
    """Vet confirms, completes, or marks no-show for their own appointment."""
    appointment = db.get(Appointment, appt_id)
    if appointment is None or appointment.vet_id != user.id:
        raise HTTPException(status_code=404, detail="Appointment not found")

    allowed = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"completed", "no_show", "cancelled"},
        "completed": set(),
        "no_show": set(),
        "cancelled": set(),
    }
    if new_status not in allowed[appointment.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move appointment from '{appointment.status}' to '{new_status}'",
        )
    appointment.status = new_status
    db.commit()
    db.refresh(appointment)
    return appointment


# ---------- Public stats ----------


@router.get("/stats", response_model=StatsOut)
def public_stats(db: Session = Depends(get_db)):
    today = utcnow().date()
    total_appts = db.scalar(select(func.count(Appointment.id))) or 0
    today_appts = (
        db.scalar(select(func.count(Appointment.id)).where(Appointment.date == today)) or 0
    )
    cities = (
        db.scalar(select(func.count(func.distinct(User.city))).where(User.is_active.is_(True))) or 0
    )
    return StatsOut(
        vets=db.scalar(
            select(func.count(User.id)).where(User.role == ROLE_VET, User.is_active.is_(True))
        )
        or 0,
        verified_vets=db.scalar(
            select(func.count(VetProfile.id)).where(VetProfile.verified.is_(True))
        )
        or 0,
        pets=db.scalar(select(func.count(Pet.id))) or 0,
        appointments_total=total_appts,
        appointments_today=today_appts,
        cities=cities,
    )
