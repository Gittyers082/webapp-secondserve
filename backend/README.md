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

## Partners, donations and delivery

- **Partners** (LGUs, agencies, charities, shelters) sign up with `role: "partner"` and a
  `partner` block, and wait for admin approval like sellers.
- A seller moves an active listing to the **Surplus Board** with
  `POST /api/listings/{id}/offer-to-partners`: `partner-offer` with a lower `partnerPrice`,
  or `donation` (free). It leaves the marketplace for good (`channel` changes).
- Partners browse `GET /api/partners/surplus` (filters: `channel`, `category`, `q`,
  `maxPrice`, `minQuantity`, `expiringSoon`, `expiresBefore`, `sort`), then
  `POST /api/partners/surplus/{id}/buy` (partner offers) or `/claim` (donations). Both lock
  the listing row like buyer orders, so two partners can't both get the last item.
- Every order picks `fulfillmentType` (`pickup` or `delivery`, plus `deliveryAddress`) from
  what the listing allows (`allowsPickup`, `allowsDelivery`). Delivery adds the listing's
  `deliveryFee`, which earns no commission.
- Delivery is simulated: `pending` until the seller marks it ready (`preparing`, handed to
  the courier), then the seller calls `POST /api/orders/{id}/delivery` with
  `out-for-delivery`, then `delivered`, which finishes the order (status `delivered`).
- Partners confirm hand-out with `POST /api/partners/orders/{id}/distributed` once the
  order is picked up or delivered.
- **Who may buy:** only partner types in `PARTNER_BUYER_TYPES` (default `lgu,government-agency`)
  can buy partner offers (`/buy` answers 403 otherwise). Every approved partner can claim
  donations. Add `charity,shelter` to the setting to let every partner buy.
- **New surplus notices:** when a seller offers a listing, or the escalation job moves it,
  approved partners get an in-app notice (donations: everyone, paid offers: partners who may
  buy). Open buyer pages are told to drop the listing.
- **Held claims:** a partner pickup order not collected within `CLAIM_HOLD_HOURS` (default 4)
  is cancelled and its stock goes back on the Surplus Board.

## Seller pages and receipts

- `GET /api/seller/reviews`: the seller's reviews (newest first, `limit`/`offset`) with
  `sellerAverage`, `sellerReviewCount` and `distribution` (stars 1 to 5).
- `GET /api/seller/sales?days=30`: completed orders in the last `days` days (Philippine
  time): `orders`, `itemsSold`, `donatedItems`, `revenue`, `commission`, `netRevenue`,
  `discountImpact`, `pendingOrders` and a `daily` series with zero days filled in.
- `GET /api/orders/{id}/receipt`: printable HTML receipt for the buyer, partner, seller or admin.

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

| Done and tested without a database | Tested against Postgres | Written, needs testing against Supabase | Still TODO |
| --- | --- | --- | --- |
| Token checking, eligibility rules, photo compression, health check, login required on routes | Reserve with row locking (no overselling), whole-cart checkout (all or nothing, no deadlocks), cancel, pickup code, reviews, typo-tolerant search | Profile sign-up, listings CRUD, notifications, admin approvals/bans, photo upload to Storage, wishlist, Redis stock pub/sub | Receipts, moderation, stats, expiry job, seller rating on listing cards |

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

### Scheduled jobs without a worker

The jobs live in `app/services/jobs.py`: expiring listings and warning sellers 3 hours
ahead, moving unsold food within `SURPLUS_WINDOW_HOURS` of expiry to the Surplus Board
(`escalate-surplus`), and releasing uncollected partner orders (`release-claims`).
On the free plan they run through
`POST /api/internal/run-jobs`, which the **Scheduled jobs** GitHub Action
(`.github/workflows/jobs.yml`) calls every 15 minutes:

1. Generate a secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Render: add `JOBS_SECRET` with that value.
3. GitHub, Settings > Secrets and variables > Actions: add the secret
   `JOBS_SECRET` (same value) and the variable `API_URL`
   (`https://secondserve-api.onrender.com`).
4. Actions tab > Scheduled jobs > Run workflow, to check it once by hand.

Without `JOBS_SECRET` the endpoint answers 404 to everyone. New jobs go in the
`JOBS` dict and must be safe to run twice.
