# Usage Guide

## Roles

| Role | What you can do |
|---|---|
| **Owner** | Register, add pets, log vaccines, view reminders, book/cancel appointments |
| **Vet** | Clinic profile, see your day queue, mark complete/no-show |
| **Admin** | Verify vet profiles so they appear in the public directory |

## Walkthrough

### 1. Create an account
Register at `/` with role **Pet owner**. Vet accounts get a profile shell
(visible only after an admin verifies them — check `api/index.py` seed or
register an admin).

### 2. Add your pet
Dashboard → **Add a pet**: name, species, breed, DOB, weight, conditions.

### 3. Vaccine reminders
Open a pet to see its computed schedule. A dog born 300 days ago with no
records shows DHPP and rabies as **overdue**; log a dose (vaccine + date) and
the next booster date is recomputed from that dose.

Statuses: `covered` (>30 days) · `upcoming` (≤30) · `due` (≤14) · `overdue`.

### 4. Book a vet
**Book a vet** tab → search by city → pick a clinic → choose a pet, date, and
one of the free 30-minute slots. Bookings confirm instantly; the ref
(`PLT-2026-000001`) is your confirmation. A 409 means someone took the slot —
pick another.

### 5. Vet flow
Log in as the vet (seed: `vet@paltoo.pk` / `vet12345`). **Today's visits**
lists the day's appointments; mark **completed** or **no-show**. The **My
clinic** tab edits your public profile (fee, bio, address).

### 6. Cancel
Owners cancel from **Appointments**; the slot frees immediately.

## Notes

- Public vet directory only shows **verified** vets.
- Appointments are confirmed immediately on booking (no double-opt-in) to keep
  the flow simple for clinics.
- Slots: 10:00–19:30 every 30 min, up to 14 days ahead (configurable).
