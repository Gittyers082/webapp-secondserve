# Team roles

Search the code for `TODO(Role N)` to find what's assigned to you.

## Role 1 — Project Lead & Head Backend

**Owns:** architecture, API contract, database schema and migrations, login and
role permissions, user profiles, admin endpoints, notifications and emails, audit log,
admin stats and data export.

**Spec:** FR-SYS-1, 2, 3, 10, 11, 12 · FR-USER-S-1–3, S-10 · FR-USER-B-1–3 · FR-BUS-7, 11 ·
NFR-SYS-S-1, 3, 6

**Code:** `backend/app/core/`, `routers/me.py`, `routers/admin.py`, `routers/notifications.py`,
`workers/`

**Project management:** sprint plan and GitHub board, branch protection, PR reviews for the
backend, merging `dev` → `main`, final say on scope.

**First week:** create the Supabase project, run the first migration, share `.env` values
privately, set up branch protection on `main` and `dev`.

## Role 2 — Head Frontend & UI/UX Designer

**Owns:** the design system (`src/styles/global.css`), components and layouts, frontend PR
reviews, accessibility and responsive layout, clear pricing display.

**Designs the missing screens:** listing detail page, wishlist and compare, reviews,
notification center, seller analytics, FAQ/help. Removes the "connect to server" screen.

**Builds:** seller and admin screens against the real API.

**Spec:** NFR-USER-U-1–10, NFR-USER-PERS-3

**First week:** remove the connect screen, list which screens are missing, agree with Role 4
who builds which page.

## Role 3 — Backend Developer: Marketplace & Orders

**Owns:** listings, eligibility rules, image upload, search/filter/sort, orders and
reservations, simulated payments, live stock over WebSockets, reviews and seller ratings.

**Spec:** FR-SYS-4–9 · FR-USER-S-4–7 · FR-USER-B-5–12, B-15 · FR-BUS-4, 8, 9 · NFR-SYS-P-4

**Code:** `backend/app/routers/listings.py`, `routers/orders.py`, `services/orders.py`,
`services/eligibility.py`, `realtime/`

**First week:** read `routers/listings.py` (the worked example) and `services/orders.py`
(the row-locking pattern), then build image upload.

## Role 4 — Frontend Developer: Buyer Flow & Integration

**Owns:** the API client (`src/lib/api.ts`), Supabase login in the browser, replacing the
sample data in `src/data/store.ts` with API calls, all buyer screens (shop, detail, search,
wishlist/compare, cart, checkout, pending, history, reviews), live stock updates,
form validation, loading/error states, offline caching, the 25-minute session warning.

**Spec:** FR-USER-B-4–15 · NFR-USER-R-1, R-4, R-5 · NFR-USER-PERS-1 · NFR-USER-PERF-1–3

**First week:** install `@supabase/supabase-js`, wire up login and register, call
`api.me.get()` to land each role on its own dashboard.

## Role 5 — QA, DevOps & Documentation

**Owns:** CI (`.github/workflows/ci.yml`), deployment (Vercel, Render via `render.yaml`,
Supabase, Upstash), testing (Postman collection, pytest integration tests, Playwright
end-to-end, usability and acceptance sessions), documentation (proposal updates in
`docs/DECISIONS.md`, ERD/DFD/use-case diagrams, terms of service and privacy pages,
backup and disaster-recovery write-up), bug triage.

**Spec:** Section VI (Testing) · NFR-SYS-M-1, M-4 · NFR-SYS-A-1, A-2 · NFR-BUS-LC-1–5

**First week:** deploy the frontend to Vercel and the API to Render, make CI pass on `dev`,
start updating the proposal from `docs/DECISIONS.md`.
