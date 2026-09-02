# Paltoo — Architecture

## Overview

Paltoo is a pet-care + vet-appointment platform for Pakistan. Pet owners
register their pets, log vaccinations, and get reminder windows computed from
real vaccine schedules. Vets publish a clinic profile; owners book 30-minute
appointment slots that are checked atomically so double-booking is impossible.

## System diagram

```
                        ┌────────────────────────────┐
                        │         Browser (SPA)       │
                        │  mobile-first vanilla JS    │
                        └──────────────┬─────────────┘
                                       │  REST (JSON) / JWT Bearer
                                       ▼
                        ┌────────────────────────────┐
                        │        FastAPI app         │
                        │  ┌──────────────────────┐  │
                        │  │ Routers              │  │
                        │  │ auth  pets  vets     │  │
                        │  │ appointments  admin  │  │
                        │  └──────────┬───────────┘  │
                        │  SlowAPI rate limits      │
                        │  CORS allow-list          │
                        │  Pydantic validation      │
                        └──────────────┬─────────────┘
                                       │ SQLAlchemy 2.0 (ORM)
                                       ▼
                        ┌────────────────────────────┐
                        │  SQLite (dev, WAL)         │
                        │  PostgreSQL 16 (prod/docker)│
                        └────────────────────────────┘
```

## Data model

- **users** — email/password-hash (bcrypt, 12 rounds), name, phone, city,
  role (`owner` | `vet` | `admin`).
- **vet_profiles** — 1:1 with users; clinic name, specialty, address, fee,
  bio, `verified` flag (admin-approved before appearing publicly).
- **pets** — owner_id, species (`dog` | `cat` | `other`), breed, gender,
  birth_date, weight, medical conditions.
- **vaccine_records** — pet_id, vaccine_key, vaccine_name, administered_on,
  recorded_by (audit trail).
- **appointments** — ref (`PLT-2026-000001`), pet/vet/owner FKs, date, slot
  (`"10:00"`), reason, status state machine, vet_notes.

## Booking flow & concurrency

1. Owner picks vet + date; GET `/api/vets/{id}/slots?date=` returns free slots.
2. POST `/api/appointments` validates: date within 14-day window, slot in the
   clinic slot list, then **re-checks availability inside the same transaction**
   before inserting. The appointment `ref` is unique, so two concurrent
   requests for the same slot cannot both insert; the loser gets `409`.
3. Slots free instantly on cancel (status → `cancelled`, excluded from live set).

Status machine: `confirmed → completed | no_show | cancelled` (bookings start
`confirmed`; `pending` exists for future extensions).

## Vaccine reminder engine

- Core schedules per species with intervals (DHPP yearly, rabies yearly,
  bordetella 6-monthly, etc.).
- First dose for puppies at 6 weeks, kittens at 8 weeks; rabies never before
  16 weeks.
- Boosters = last administered dose + interval.
- Status per vaccine: `covered` (>30d away), `upcoming` (≤30d), `due` (≤14d),
  `overdue` (<0d).

## Security

- JWT HS256 (24h expiry), bcrypt(12) hashing.
- SlowAPI rate limits: register 5/min, login 10/min, default 60/min.
- Role guards on every protected route; owner routes only return the caller's
  own pets/appointments; foreign access returns `404` (no existence leak).
- Pydantic validation on all inputs; secrets only in env; CORS allow-list.

## Scaling notes

- SQLite (WAL) for dev and the Vercel /tmp fallback; PostgreSQL 16 via
  docker-compose for production.
- Slots are derived from config (10:00–20:00, 30-min) — no slot table to
  backfill; scale is bounded by appointment rows, which index on
  `(vet_id, date)`.
- The SPA is static; the whole app runs as a single serverless function on
  Vercel (`api/index.py`), or as a container on any host.

## Tech stack

FastAPI 0.115 · Python 3.11 · SQLAlchemy 2.0 · Pydantic v2 · JWT · bcrypt ·
SlowAPI · vanilla JS SPA · Docker/Postgres 16 · Vercel-ready.