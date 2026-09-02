"""SQLAlchemy ORM models for Paltoo."""

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLE_OWNER = "owner"
ROLE_VET = "vet"
ROLE_ADMIN = "admin"
ROLES = (ROLE_OWNER, ROLE_VET, ROLE_ADMIN)

SPECIES = ("dog", "cat", "other")
GENDERS = ("male", "female")

APPT_PENDING = "pending"
APPT_CONFIRMED = "confirmed"
APPT_COMPLETED = "completed"
APPT_CANCELLED = "cancelled"
APPT_NO_SHOW = "no_show"
APPT_LIVE = (APPT_PENDING, APPT_CONFIRMED)


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=ROLE_OWNER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vet_profile: Mapped["VetProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    pets: Mapped[list["Pet"]] = relationship(back_populates="owner")


class VetProfile(Base):
    __tablename__ = "vet_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    clinic_name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), default="General practice")
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    fee_pkr: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    bio: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="vet_profile")

    @property
    def owner(self) -> "User":
        """Alias so response schemas can expose the owning user as 'owner'."""
        return self.user


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    species: Mapped[str] = mapped_column(String(20), nullable=False, default="dog")
    breed: Mapped[str] = mapped_column(String(120), default="")
    gender: Mapped[str] = mapped_column(String(10), default="male")
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, default=1.0)
    medical_conditions: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["User"] = relationship(back_populates="pets")
    vaccine_records: Mapped[list["VaccineRecord"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="pet")


class VaccineRecord(Base):
    """A vaccine administration actually logged against a pet."""

    __tablename__ = "vaccine_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True, nullable=False)
    vaccine_key: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. 'dhpp'
    vaccine_name: Mapped[str] = mapped_column(String(120), nullable=False)
    administered_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pet: Mapped["Pet"] = relationship(back_populates="vaccine_records")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True, nullable=False)
    vet_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    slot: Mapped[str] = mapped_column(String(5), nullable=False)  # "10:00"
    reason: Mapped[str] = mapped_column(String(255), default="General checkup")
    status: Mapped[str] = mapped_column(String(20), default=APPT_PENDING, index=True)
    vet_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pet: Mapped["Pet"] = relationship(back_populates="appointments")
    vet: Mapped["User"] = relationship(foreign_keys=[vet_id])
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
