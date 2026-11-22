# SecondServe API (backend)

FastAPI + SQLAlchemy (async) on Supabase Postgres. Supabase Auth handles sign-up,
login and password hashing; this API checks the token on every request.

## First-time setup (everyone)

You need **Python 3.10+** (3.12 recommended) and Git.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Ask the project lead for the values in `.env`. **Never commit `.env`.**

```powershell
alembic upgrade head            # create/update the tables
uvicorn app.main:app --reload   # http://localhost:8000
```

Open <http://localhost:8000/docs> for the interactive API docs. They're generated
from the code, so they're always the current API contract for the frontend.

Run the tests and the linter before every PR:

```powershell
pytest
ruff check .
```

## One-time Supabase setup (project lead)

1. Create a project at supabase.com (region: Southeast Asia / Singapore).
2. **Database URL:** Connect → *Session pooler* → copy the URI into `DATABASE_URL`,
   and change `postgresql://` to `postgresql+asyncpg://`.
3. **Auth:** Settings → API → copy the project URL into `SUPABASE_URL`.
   If the project shows a legacy *JWT secret*, put it in `SUPABASE_JWT_SECRET`;
   if it uses the new *JWT signing keys*, leave that empty (the API reads the public keys itself).
4. **30-minute sessions (NFR-SYS-S-1):** Auth settings → set access token expiry to 1800 seconds.
5. **Storage:** create a public bucket named `listing-images`.
6. Create the first migration from the models and commit it:
   ```powershell
   alembic upgrade head                                  # enables pg_trgm
   alembic revision --autogenerate -m "initial schema"
   alembic upgrade head
   ```
   Read the generated file in `alembic/versions/` before committing it.
7. **First admin:** sign up through the app as a normal user, then run this in the
   Supabase SQL editor:
   ```sql
   update users set role = 'admin', status = 'active' where email = 'you@example.com';
   ```

After the first migration, anyone who changes a model runs
`alembic revision --autogenerate -m "what changed"` and commits the file with their PR.

## How a request is checked

```
Browser ──(Bearer token from supabase-js)──▶ FastAPI
  get_token_claims   verify the token's signature and expiry        → 401 if bad
  get_current_user   load our users row                             → 403 "profile_missing"
  require_role(...)  buyer / seller / admin, and account approved   → 403
```

Sellers start as `pending` and can't list anything until an admin approves them
(FR-BUS-7). Buyers are active right away.

## Folder layout

```
app/
  main.py              app setup: CORS, rate limiting, routers
  core/                config, token checking, dependencies, rate limiter
  db/                  engine, session, base model classes
  models/              database tables (mirror the ERD and src/data/types.ts)
  schemas/             request/response shapes (JSON is camelCase, like types.ts)
  services/            business logic: eligibility rules, orders, notifications, audit
  routers/             HTTP endpoints, one file per area
  realtime/            WebSocket stock broadcaster
  workers/             Celery app and background tasks (emails, expiry)
alembic/               database migrations
tests/                 pytest
```

## Who owns what

| Area | Files | Owner |
| --- | --- | --- |
| Auth, profiles, admin, notifications, audit, emails, reports | `core/`, `routers/me.py`, `routers/admin.py`, `routers/notifications.py`, `workers/` | Role 1, Project Lead |
| Listings, search, images, orders, payments, live stock, reviews | `routers/listings.py`, `routers/orders.py`, `services/orders.py`, `realtime/` | Role 3, Backend Developer |
| Tests, CI, deployment | `tests/`, `.github/workflows/`, `render.yaml` | Role 5, QA & DevOps |

Search the code for `TODO(Role N)` to find your next task.

## Adding an endpoint

Copy the pattern in `routers/listings.py`:

1. Request/response schemas go in `schemas/` (extend `Schema` so JSON is camelCase).
2. Put the rules in `services/` so they can be unit tested without HTTP.
3. In the route: take `db: DB` and a role guard (`ActiveSeller`, `ActiveBuyer`, `Admin`,
   `CurrentUser`), do the work, call `audit.record(...)` for important actions, then `await db.commit()`.
4. Write a test in `tests/`.

## Status of what's built

| Done and tested without a database | Written, needs testing against Supabase | Still TODO |
| --- | --- | --- |
| Token checking, eligibility rules, health check, login required on routes | Profile sign-up, listings CRUD + browse/filter/sort, reserve with row locking, notifications, admin approvals/bans | Image upload, checkout of a whole cart, ready/picked-up/cancel, reviews, receipts, moderation, stats, expiry job |

## Deploying

Render reads `render.yaml` at the repo root. Set the same variables as `.env` in
the Render dashboard. Render's free tier sleeps after inactivity, so the first
request after a while is slow. Open the app before a demo.

Celery needs a separate worker process. Until that's running, keep
`CELERY_ENABLED=false`: in-app notifications still work, emails are just skipped.
