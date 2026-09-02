# Setup Guide

## Prerequisites

- Python 3.11+
- (Optional) Docker + Docker Compose for the Postgres path
- (Optional) Vercel CLI for deployment

## 1. Local (SQLite)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-26-paltoo.git
cd day-26-paltoo

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# At minimum set a real SECRET_KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — the SPA loads at `/` and the API docs at
`/docs`. On first boot the app creates `paltoo.db` (SQLite WAL) and seeds
demo accounts (see README).

## 2. Docker + PostgreSQL

```bash
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` runs Postgres 16 with a healthcheck; the API waits for it
and uses `DATABASE_URL=postgresql+psycopg2://paltoo:paltoo@db:5432/paltoo`.

## 3. Configuration

All config via environment (see `.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | dev value | **must** change in production |
| `DATABASE_URL` | `sqlite:///./paltoo.db` | Postgres in prod |
| `CORS_ORIGINS` | `*` | comma-separated in prod |
| `APP_ENV` | `development` | `production` on deploy |
| `ACCESS_TOKEN_MINUTES` | `1440` | JWT lifetime |
| `BOOKING_DAYS_AHEAD` | `14` | booking window |
| `CLINIC_OPEN_HOUR` / `CLINIC_CLOSE_HOUR` | `10` / `20` | slot bounds |

## 4. Vercel deploy (one-time, on your machine)

```bash
npm i -g vercel
vercel login
vercel --prod
```

The repo ships `vercel.json` + `api/index.py` (serverless entry). Vercel's
filesystem is read-only/ephemeral, so the function falls back to
`sqlite:////tmp/paltoo.db`. For a persistent deployment, set the
`DATABASE_URL` env var on Vercel to a managed Postgres.

> Note: automated deploy from the build sandbox is blocked (no
> `VERCEL_TOKEN`, no interactive login) — verified locally instead.

## 5. Smoke-test transcript (local production build)

```text
GET  /api/health            -> 200 {"status":"ok","app":"paltoo",...}
GET  /                      -> 200 (SPA index.html)
GET  /api/stats             -> 200 {"vets":1,"verified_vets":1,...}
POST /api/auth/register     -> 201 + JWT + user
POST /api/auth/login        -> 200 + JWT (vet@paltoo.pk)
GET  /api/vets              -> 200 [Paws & Claws...]
GET  /api/vets/2/slots?date -> 200 20 free slots (10:00..19:30)
GET  /api/pets (no token)   -> 401
```

All routes verified with `uvicorn` + `curl` against the production entry.
