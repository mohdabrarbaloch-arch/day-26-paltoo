"""Pydantic request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import GENDERS, ROLES, SPECIES

# ---------- Auth ----------


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    city: str = Field(min_length=2, max_length=60)
    role: str = Field(default="owner")

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        v = v.lower()
        if v not in ROLES:
            raise ValueError("role must be one of owner, vet, admin")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone: str
    city: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VetProfileCreate(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=150)
    specialty: str = Field(default="General practice", max_length=120)
    address: str = Field(min_length=5, max_length=255)
    fee_pkr: int = Field(ge=0, le=100_000)
    bio: str = Field(default="", max_length=2000)


class VetProfileUpdate(BaseModel):
    clinic_name: str | None = Field(default=None, min_length=2, max_length=150)
    specialty: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    fee_pkr: int | None = Field(default=None, ge=0, le=100_000)
    bio: str | None = Field(default=None, max_length=2000)


class VetProfileOut(BaseModel):
    id: int
    clinic_name: str
    specialty: str
    address: str
    fee_pkr: int
    bio: str
    verified: bool
    user_id: int
    owner: UserOut

    model_config = {"from_attributes": True}


# ---------- Pets ----------


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    species: str = "dog"
    breed: str = Field(default="", max_length=120)
    gender: str = Field(default="male")
    birth_date: date
    weight_kg: float = Field(default=1.0, ge=0.05, le=200)
    medical_conditions: str = Field(default="", max_length=2000)

    @field_validator("species")
    @classmethod
    def species_valid(cls, v: str) -> str:
        v = v.lower()
        if v not in SPECIES:
            raise ValueError("species must be one of dog, cat, other")
        return v

    @field_validator("gender")
    @classmethod
    def gender_valid(cls, v: str) -> str:
        v = v.lower()
        if v not in GENDERS:
            raise ValueError("gender must be male or female")
        return v

    @field_validator("birth_date")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("birth date cannot be in the future")
        return v


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    breed: str | None = Field(default=None, max_length=120)
    gender: str | None = None
    weight_kg: float | None = Field(default=None, ge=0.05, le=200)
    medical_conditions: str | None = Field(default=None, max_length=2000)


class PetOut(BaseModel):
    id: int
    name: str
    species: str
    breed: str
    gender: str
    birth_date: date
    weight_kg: float
    medical_conditions: str
    age_years: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VaccineRecordCreate(BaseModel):
    vaccine_key: str = Field(min_length=2, max_length=40)
    administered_on: date
    notes: str = Field(default="", max_length=1000)

    @field_validator("administered_on")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("administered date cannot be in the future")
        return v


class VaccineRecordOut(BaseModel):
    id: int
    vaccine_key: str
    vaccine_name: str
    administered_on: date
    notes: str
    recorded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReminderOut(BaseModel):
    key: str
    name: str
    due_date: date
    days_left: int
    status: str


class PetDetailOut(BaseModel):
    pet: PetOut
    reminders: list[ReminderOut]
    reminder_summary: dict


# ---------- Appointments ----------


class AppointmentCreate(BaseModel):
    vet_id: int
    pet_id: int
    date: date
    slot: str = Field(pattern=r"^\d{2}:\d{2}$")
    reason: str = Field(default="General checkup", min_length=2, max_length=255)


class AppointmentUpdate(BaseModel):
    status: str


class AppointmentOut(BaseModel):
    id: int
    ref: str
    date: date
    slot: str
    reason: str
    status: str
    vet_notes: str
    vet: UserOut
    pet: PetOut
    created_at: datetime

    model_config = {"from_attributes": True}


class AvailableSlotsOut(BaseModel):
    date: date
    slots: list[str]


# ---------- Stats ----------


class StatsOut(BaseModel):
    vets: int
    verified_vets: int
    pets: int
    appointments_total: int
    appointments_today: int
    cities: int


# ---------- Misc ----------


class MessageOut(BaseModel):
    detail: str


class VaccineOptionsOut(BaseModel):
    species: str
    vaccines: list[dict]
