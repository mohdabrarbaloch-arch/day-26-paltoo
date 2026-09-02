"""Pet management + vaccine records + reminder computation.

Owner-only routes (scoped to pets the owner actually owns).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import ROLE_OWNER, Pet, User, VaccineRecord
from ..schemas import (
    PetCreate,
    PetDetailOut,
    PetOut,
    PetUpdate,
    ReminderOut,
    VaccineOptionsOut,
    VaccineRecordCreate,
    VaccineRecordOut,
)
from ..security import get_current_user, require_roles
from ..services import vaccines

router = APIRouter(prefix="/api", tags=["pets"])


def _own_pet_or_404(db: Session, pet_id: int, user: User) -> Pet:
    pet = db.get(Pet, pet_id)
    if pet is None or pet.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def _load_pet_full(db: Session, pet_id: int) -> Pet:
    pet = db.scalar(select(Pet).where(Pet.id == pet_id).options(selectinload(Pet.vaccine_records)))
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def _pet_out(pet: Pet) -> PetOut:
    data = PetOut.model_validate(pet)
    data.age_years = round((date.today() - pet.birth_date).days / 365.25, 1)
    return data


# ---------- CRUD ----------


@router.post("/pets", response_model=PetOut, status_code=201)
def create_pet(
    payload: PetCreate,
    user: User = Depends(require_roles(ROLE_OWNER)),
    db: Session = Depends(get_db),
):
    pet = Pet(owner_id=user.id, **payload.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _pet_out(pet)


@router.get("/pets", response_model=list[PetOut])
def list_pets(
    user: User = Depends(require_roles(ROLE_OWNER)),
    db: Session = Depends(get_db),
):
    pets = db.scalars(
        select(Pet).where(Pet.owner_id == user.id).order_by(Pet.created_at.desc())
    ).all()
    return [_pet_out(p) for p in pets]


@router.get("/pets/{pet_id}", response_model=PetDetailOut)
def pet_detail(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pet = _load_pet_full(db, pet_id)
    if pet.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Pet not found")
    reminders = vaccines.compute_reminders(pet)
    return PetDetailOut(
        pet=_pet_out(pet),
        reminders=[ReminderOut.model_validate(r.__dict__) for r in reminders],
        reminder_summary=vaccines.summary_counts(reminders),
    )


@router.patch("/pets/{pet_id}", response_model=PetOut)
def update_pet(
    pet_id: int,
    payload: PetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pet = _own_pet_or_404(db, pet_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(pet, key, value)
    db.commit()
    db.refresh(pet)
    return _pet_out(pet)


@router.delete("/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pet = _own_pet_or_404(db, pet_id, user)
    db.delete(pet)
    db.commit()


# ---------- Vaccine records ----------


@router.get("/vaccines/options", response_model=list[VaccineOptionsOut])
def vaccine_options(db: Session = Depends(get_db)):
    return [
        VaccineOptionsOut(species="dog", vaccines=vaccines.vaccine_key_options("dog")),
        VaccineOptionsOut(species="cat", vaccines=vaccines.vaccine_key_options("cat")),
    ]


@router.post("/pets/{pet_id}/vaccines", response_model=VaccineRecordOut, status_code=201)
def add_vaccine_record(
    pet_id: int,
    payload: VaccineRecordCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner logs a dose for their own pet."""
    pet = _own_pet_or_404(db, pet_id, user)
    try:
        meta = vaccines.vaccines_for_species(pet.species)[payload.vaccine_key]
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"vaccine '{payload.vaccine_key}' is not available for {pet.species}",
        ) from None
    record = VaccineRecord(
        pet_id=pet.id,
        vaccine_key=payload.vaccine_key,
        vaccine_name=meta["name"],
        administered_on=payload.administered_on,
        notes=payload.notes,
        recorded_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return VaccineRecordOut.model_validate(record)


@router.get("/pets/{pet_id}/vaccines", response_model=list[VaccineRecordOut])
def list_vaccine_records(
    pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    pet = _own_pet_or_404(db, pet_id, user)
    records = db.scalars(
        select(VaccineRecord)
        .where(VaccineRecord.pet_id == pet.id)
        .order_by(VaccineRecord.administered_on.desc())
    ).all()
    return [VaccineRecordOut.model_validate(r) for r in records]
