"""Admin routes: verify vets, promote users, see platform-wide stats."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ROLE_ADMIN, User, VetProfile
from ..schemas import UserOut, VetProfileOut
from ..security import require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/vets", response_model=list[VetProfileOut])
def admin_list_vets(
    verified_only: bool = False,
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    query = (
        select(VetProfile).join(User, User.id == VetProfile.user_id).order_by(VetProfile.created_at)
    )
    if verified_only:
        query = query.where(VetProfile.verified.is_(True))
    return db.scalars(query).all()


@router.post("/vets/{vet_id}/verify", response_model=VetProfileOut)
def verify_vet(
    vet_id: int,
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    profile = db.get(VetProfile, vet_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Vet profile not found")
    profile.verified = True
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/users/{user_id}/promote", response_model=UserOut)
def promote_user(
    user_id: int,
    role: str,
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Promote a user to vet (assigns them a profile shell) or admin."""
    if role not in ("vet", "admin"):
        raise HTTPException(status_code=422, detail="Role must be 'vet' or 'admin'")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    if role == "vet":
        existing = db.scalar(select(VetProfile).where(VetProfile.user_id == user.id))
        if existing is None:
            db.add(
                VetProfile(
                    user_id=user.id,
                    clinic_name=f"{user.name}'s clinic",
                    address=f"{user.city} area",
                    fee_pkr=1500,
                    bio="",
                )
            )
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    _admin: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    return db.scalars(query).all()
