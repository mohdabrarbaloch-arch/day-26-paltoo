"""Shared pytest fixtures: isolated DB per test, authenticated clients."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(
    client,
    email="owner@test.pk",
    password="owner1234",
    name="Test Owner",
    city="Karachi",
    role="owner",
):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": name,
            "phone": "0300-0000000",
            "city": city,
            "role": role,
        },
    )


def auth_headers(client, email="owner@test.pk", password="owner1234"):
    res = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def make_owner(client, **kw):
    register(client, **kw)
    return auth_headers(client, kw.get("email", "owner@test.pk"), kw.get("password", "owner1234"))


def make_vet(client):
    register(
        client, email="vet@test.pk", password="vet12345", name="Dr. Vet", city="Lahore", role="vet"
    )
    return auth_headers(client, "vet@test.pk", "vet12345")


def make_admin(client):
    register(
        client,
        email="admin@test.pk",
        password="admin1234",
        name="Admin",
        city="Karachi",
        role="admin",
    )
    return auth_headers(client, "admin@test.pk", "admin1234")
