"""FastAPI app entrypoint. Wire routers, middleware, and startup seed."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .database import SessionLocal, init_db
from .models import ROLE_ADMIN, ROLE_VET, User, VetProfile
from .routers import admin as admin_router
from .routers import appointments as appointments_router
from .routers import auth as auth_router
from .routers import pets as pets_router
from .routers import vets as vets_router
from .security import hash_password

limiter = Limiter(key_func=get_remote_address)


def _seed() -> None:
    """Idempotent dev seed: demo users + verified vet profile."""
    db = SessionLocal()
    try:
        from sqlalchemy import select

        if db.scalar(select(User).where(User.email == "admin@paltoo.pk")):
            return
        db.add(
            User(
                email="admin@paltoo.pk",
                password_hash=hash_password("admin12345"),
                name="Platform Admin",
                phone="0300-0000000",
                city="Karachi",
                role=ROLE_ADMIN,
            )
        )
        vet_user = User(
            email="vet@paltoo.pk",
            password_hash=hash_password("vet12345"),
            name="Dr. Ayesha Khan",
            phone="0301-1111111",
            city="Karachi",
            role=ROLE_VET,
        )
        db.add(vet_user)
        db.flush()
        db.add(
            VetProfile(
                user_id=vet_user.id,
                clinic_name="Paws & Claws Veterinary Clinic",
                specialty="Small animals & surgery",
                address="Shop 12, Block B, Gulshan-e-Iqbal, Karachi",
                fee_pkr=2000,
                bio=(
                    "Certified small-animal vet with 8 years of experience in "
                    "vaccinations, surgery and pet nutrition."
                ),
                verified=True,
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _seed()
    yield


app = FastAPI(title="Paltoo API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router.router)
app.include_router(pets_router.router)
app.include_router(vets_router.router)
app.include_router(appointments_router.router)
app.include_router(admin_router.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": "paltoo", "env": settings.app_env}


# Static SPA (must come last so /api and docs keep priority).
app.mount("/", StaticFiles(directory="public", html=True), name="public")
