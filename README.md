# 🐾 Paltoo — پالتو

> Pet care jo kabhi miss na ho. Register your pets, track vaccinations, get
> smart reminders, and book verified vets online — for Pakistan's pet parents.

![python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![fastapi](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![tests](https://img.shields.io/badge/tests-41%20passing-2ea44f)
![license](https://img.shields.io/badge/license-MIT-blue)

---

## The problem

Pet care in Pakistan still runs on WhatsApp and phone calls. "Beta, vaccination
kab thi?" — nobody remembers. Clinics manage paper diaries, owners forget
boosters, and booking a vet means calling around to ask *kal kya time khaali
hai*. Paltoo fixes that: one place for your pet's records, reminders before
vaccines go overdue, and online booking with real free-slot visibility.

## Features

- **🐶 Pet profiles** — dogs, cats & others, with breed, DOB, weight, medical notes
- **💉 Vaccine records + smart reminders** — species-specific schedules (DHPP,
  FVRCP, rabies, lepto & more); overdue/due/upcoming computed from age + last dose
- **🩺 Verified vet directory** — search by city, view clinic, specialty, fees
- **📅 Double-booking-proof appointments** — 30-min slots, atomic check-and-book,
  refs like `PLT-2026-000001`, cancel frees the slot instantly
- **👥 Three roles** — owner, vet (clinic profile, today's queue, complete/no-show),
  admin (verify vets)
- **📊 Public stats** — vets, pets, appointments, cities served
- **📱 Mobile-first dark SPA** — zero build step, works on any phone
- **🔐 Security** — JWT + bcrypt(12), rate limits, role guards, scoped queries

## Demo accounts (dev seed)

| Role | Email | Password |
|---|---|---|
| Owner | (register your own) | — |
| Vet | `vet@paltoo.pk` | `vet12345` |
| Admin | `admin@paltoo.pk` | `admin12345` |

## Tech stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT · bcrypt · SlowAPI · vanilla JS SPA · SQLite/PostgreSQL · Docker · Vercel-ready

## Install & run locally

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-26-paltoo.git
cd day-26-paltoo

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # tweak SECRET_KEY / DATABASE_URL if you like

uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

### Docker + PostgreSQL

```bash
cp .env.example .env
docker compose up --build
# open http://localhost:8000
```

### Tests & lint

```bash
pytest            # 41 tests
ruff check app tests api
black --check app tests api
```

## API quick reference

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | create account (owner/vet/admin) | — |
| POST | `/api/auth/login` | OAuth2 form → JWT | — |
| GET | `/api/vets?city=` | public verified vets | — |
| GET | `/api/vets/{id}/slots?date=` | free slots for a day | — |
| GET | `/api/stats` | platform stats | — |
| POST | `/api/pets` | add a pet | owner |
| GET | `/api/pets` | my pets | owner |
| GET | `/api/pets/{id}` | pet + vaccine reminders | owner |
| POST | `/api/pets/{id}/vaccines` | log a vaccine dose | owner |
| POST | `/api/appointments` | book a slot (409 if taken) | owner |
| GET | `/api/appointments` | my appointments | owner/vet |
| POST | `/api/appointments/{id}/cancel` | cancel + free slot | owner |
| GET | `/api/me/vet/appointments?date=` | vet's day queue | vet |
| POST | `/api/me/vet/appointments/{id}/status` | confirm/complete/no-show | vet |
| GET/PATCH | `/api/me/vet-profile` | own clinic profile | vet |
| GET/POST | `/api/admin/vets` , `/verify` | verify vets | admin |

Full reference in [`docs/api.md`](docs/api.md).

## Screenshots

> Screenshots will be added once the project is deployed to a live URL.
> The app is fully usable locally — run it and open `http://127.0.0.1:8000`.

## Live demo

Deployment is currently **blocked**: no `VERCEL_TOKEN` is available in the
build environment and interactive `vercel login` is not possible in the
sandbox (same blocker as Days 1–25). The repo is fully deploy-ready:
`vercel.json` + `api/index.py` (serverless entry, `/tmp` SQLite fallback).
Deploy with:

```bash
vercel --prod --yes   # after `vercel login` on your machine
```

Local production build verified — all API routes respond correctly (see
[`docs/setup.md`](docs/setup.md) for the smoke-test transcript).

## Project structure

```
app/
  main.py            # FastAPI app, middleware, seed
  config.py          # pydantic-settings, env-driven
  database.py        # engine/session, WAL pragma
  models.py          # ORM models
  schemas.py         # Pydantic schemas
  security.py        # JWT + bcrypt helpers
  services/
    vaccines.py      # vaccine schedules + reminders
    slots.py         # slot generation + availability
  routers/           # auth, pets, vets, appointments, admin
public/              # SPA (index.html, styles.css, app.js)
api/index.py         # Vercel serverless entry
tests/               # 41 pytest tests
```

## Roadmap

- [ ] Email/WhatsApp reminders for due vaccines
- [ ] Payment/advance for bookings
- [ ] Vet reviews & ratings
- [ ] Multiple clinics per vet

## License

MIT — see [LICENSE](LICENSE).

---

Made for pet parents of Pakistan 🇵🇰 — Day 26 of the 30-day build challenge.