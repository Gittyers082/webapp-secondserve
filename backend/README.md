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

Sellers and partners start as `pending` and can't list or order until an admin approves
them (FR-BUS-7). Buyers are active right away.

## Partners, donations and delivery

- **Partners** (food banks, NGOs, resellers) sign up with `role: "partner"` plus a `partner`
  block, and need admin approval like sellers.
- A seller can **convert** an active listing with `POST /api/listings/{id}/convert`
  (`partner-offer` with a lower `partnerPrice`, or `donation`, which is free). It leaves the
  marketplace for good and shows on the **Surplus Board**, `GET /api/surplus`
  (partners only; filters: `kind`, `category`, `q`, `maxPrice`, `minQuantity`,
  `expiringSoon`, `expiresBefore`, `sort`).
- Buyers order retail listings and partners order Surplus Board listings, both with the
  same `POST /api/orders` and `/api/orders/checkout`. Each locks the listing row, so two
  partners can't both claim the last donation.
- Each listing has `fulfillment`: `pickup`, `delivery` or `both`. An order picks
  `fulfillment` and, for delivery, a `deliveryAddress`. Delivery adds a flat
  `DELIVERY_FEE` (no commission on it). `amountDue` is `total + deliveryFee`.
- Delivery is simulated. The seller marks the order ready (handed to the "courier", gets a
  `DLV-` reference), then `POST /api/orders/{id}/delivery` with `out-for-delivery`, then
  `delivered`. For delivery orders, order status `picked-up` means delivered.

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
| Listings, search, images, orders, payments, delivery, Surplus Board, live stock, reviews | `routers/listings.py`, `routers/orders.py`, `routers/surplus.py`, `services/orders.py`, `services/search.py`, `services/delivery.py`, `realtime/` | Role 3, Backend Developer |
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

| Done and tested without a database | Tested against Postgres | Written, needs testing against Supabase | Still TODO |
| --- | --- | --- | --- |
| Token checking, eligibility rules, photo compression, partner and delivery input rules, health check, login required on routes | Reserve with row locking (no overselling, also for donation claims), whole-cart checkout (all or nothing, no deadlocks), cancel, pickup code, reviews, typo-tolerant search, convert to partner offer or donation, Surplus Board filters, delivery flow | Profile sign-up, listings CRUD, notifications, admin approvals/bans, photo upload to Storage, wishlist, Redis stock pub/sub | Receipts, moderation, stats, expiry job, seller rating on listing cards |

### Running the Postgres tests

Row locking can't be tested without a real database. Point `TEST_DATABASE_URL` at a
**throwaway** database (its tables are dropped and recreated on every test), never Supabase:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/secondserve_test"
pytest
```

Without it those tests are skipped and `pytest` still passes.

### Live stock across instances

With `REDIS_URL` set, stock changes go through Redis pub/sub and every API instance
forwards them to its own WebSockets. Without it, only the instance that handled the
request notifies its browsers. Postgres is always the source of truth for quantities.

## Deploying

Render reads `render.yaml` at the repo root. Set the same variables as `.env` in
the Render dashboard. Render's free tier sleeps after inactivity, so the first
request after a while is slow. Open the app before a demo.

Celery needs a separate worker process. Until that's running, keep
`CELERY_ENABLED=false`: in-app notifications still work, emails are just skipped.
