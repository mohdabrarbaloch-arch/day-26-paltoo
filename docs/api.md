# API Reference

Base URL: `/api`. Auth: `Authorization: Bearer <jwt>` unless noted.
Errors return `{"detail": "..."}` with proper status codes.

## Auth

### POST /auth/register — 201
```json
{ "email": "a@b.pk", "password": "pass1234", "name": "Ali",
  "phone": "0300-1234567", "city": "Karachi", "role": "owner" }
```
Returns `{ access_token, token_type, user }`. 409 if email exists; 422 on
weak password / bad role.

### POST /auth/login — 200
OAuth2 form: `username` + `password` → `{ access_token, token_type, user }`.

### GET /auth/me — 200 · auth
Returns the current user.

## Public

### GET /vets?city=&specialty= — 200
Verified vets (nested `owner`).

### GET /vets/{vet_id} — 200 · 404 if missing/not a verified vet.

### GET /vets/{vet_id}/slots?date=YYYY-MM-DD — 200
`{ "date": "...", "slots": ["10:00", ...] }`. Empty list outside window.

### GET /vaccines/options — 200
Per-species vaccine keys/names/intervals.

### GET /stats — 200
`{ vets, verified_vets, pets, appointments_total, appointments_today, cities }`.

## Pets (owner)

### POST /pets — 201 · owner
`{ name, species: dog|cat|other, breed?, gender, birth_date, weight_kg?, medical_conditions? }`

### GET /pets — 200 · owner — your pets with `age_years`.

### GET /pets/{pet_id} — 200 · owner
`{ pet, reminders: [{key,name,due_date,days_left,status}], reminder_summary }`
Foreign pet → 404.

### PATCH /pets/{pet_id} · DELETE /pets/{pet_id} (204) · owner

### POST /pets/{pet_id}/vaccines — 201 · owner
`{ vaccine_key, administered_on, notes? }` → record with resolved name.
Unknown vaccine for species → 422.

### GET /pets/{pet_id}/vaccines — 200 · owner

## Appointments

### POST /appointments — 201 · owner
`{ vet_id, pet_id, date, slot: "HH:MM", reason? }`
- 404 pet/vet missing or foreign pet; 422 out of window/bad slot; **409 slot
  already taken (double-booking guard)**.
- Response includes `ref`, pet & vet objects, `status: "confirmed"`.

### GET /appointments?upcoming_only=true — 200 · owner or vet
Owner → own pets' appointments; vet → own calendar.

### GET /appointments/{appt_id} — 200 · owner/vet of the appointment else 404.

### POST /appointments/{appt_id}/cancel — 200 · owner
Status → `cancelled`, slot freed. 409 if not live; 404 if not yours.

## Vet

### GET /me/vet-profile — 200 · vet — own profile.
### POST /me/vet-profile — 201 · vet (409 if exists).
### PATCH /me/vet-profile — 200 · vet — partial update.

### GET /me/vet/appointments?date=&status= — 200 · vet
### POST /me/vet/appointments/{id}/status?new_status= — 200 · vet
Transitions allowed:
`confirmed → completed | no_show | cancelled`; `pending → confirmed | cancelled`.
Illegal transition → 409; foreign appointment → 404.

## Admin

### GET /admin/vets?verified_only= — 200 · admin — all profiles incl. unverified.
### POST /admin/vets/{profile_id}/verify — 200 · admin — marks verified.
### GET /admin/users?role= — 200 · admin
### POST /admin/users/{user_id}/promote?role=vet|admin — 200 · admin

## Status codes used

- 200 OK · 201 Created · 204 No Content
- 401 Unauthenticated / bad token / wrong credentials
- 403 Authenticated but wrong role
- 404 Resource missing **or foreign** (no existence leak)
- 409 Duplicate email / slot taken / illegal state transition
- 422 Validation error (Pydantic)

## Example flow

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -d "username=vet@paltoo.pk&password=vet12345" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/api/me/vet/appointments?date=$(date +%F) \
  -H "Authorization: Bearer $TOKEN"
```
