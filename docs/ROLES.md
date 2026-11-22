# Team roles

Search the code for `TODO(Role N)` to find what's assigned to you. Spec IDs refer to the
IT 313 document (v13). Cite the requirement and test case IDs in commit and PR messages.

## Role 1 — Project Lead & Head Backend (El Steven D. Cruz)

**Owns:** architecture, API contract, database schema and migrations (including the partner
profile and order fulfillment fields), login and permissions for all four roles, sessions,
rate limiting, accounts and partner registration, admin endpoints (seller and partner
approvals, bans, moderation), audit logs, Celery and Resend notifications, the surplus
escalation job and partner notifications, analytics, data export and impact reports.

**Spec:** FR-SYS-1, 2, 3, 10, 11, 12, 14, 15 · FR-USER-S-1–3, S-10 · FR-USER-B-1–3 ·
FR-USER-P-1–3, P-8 · FR-BUS-7, 11, 14 · NFR-SYS-S-1, 3, 6 · NFR-BUS-RA-1–3 · UC-16–18

**Code:** `backend/app/core/`, `routers/me.py`, `routers/admin.py`, `routers/notifications.py`,
`workers/`, `alembic/`

**Project management:** sprint plan and GitHub board, branch protection, backend PR reviews,
merging `dev` into `main`, final say on scope.

## Role 2 — Head Frontend & UI/UX Designer (Shanelle Margaret T. Navarro)

**Owns:** the design system (`src/styles/global.css`), components and layouts, frontend PR
reviews, accessibility, responsive layout and clear pricing.

**Designs:** the missing screens, the pickup or delivery choice at checkout, delivery status
on orders, and the partner screens.

**Builds:** seller screens (including fulfillment settings and Offer to Partners / Donate)
and admin screens (including partner approvals).

**Spec:** FR-USER-S-8, S-12, S-13 (screens) · NFR-USER-U-1–10 · NFR-USER-PERS-3

## Role 3 — Backend: Marketplace, Orders & Fulfillment (Ethan Christan M. Villegas)

**Owns:** listings, eligibility rules, per-listing fulfillment options, converting a listing
to a partner offer or donation, image upload, search including Surplus Board filters,
orders, partner purchases and donation claims with row locking, pickup and delivery
(address, fee, simulated courier hand-off, delivery status), simulated payments and
commission, live stock, reviews.

**Spec:** FR-SYS-4–9, 13 · FR-USER-S-4–7, S-12, S-13 · FR-USER-B-5, B-6, B-15 ·
FR-USER-P-4–7, P-9 · FR-BUS-4, 8, 9, 13 · NFR-SYS-P-4

**Code:** `backend/app/routers/listings.py`, `routers/orders.py`, `routers/partners.py`,
`services/orders.py`, `services/eligibility.py`, `services/images.py`, `realtime/`

## Role 4 — Frontend: Buyer & Partner Flow, Integration (Hans Rainier M. Fernandez)

**Owns:** the API client (`src/api/client.ts`), Supabase login for all roles including partner
registration, the 25-minute session warning, all buyer screens (including the pickup or
delivery choice at checkout and delivery status), the partner screens (Surplus Board, buy
surplus, claim donation, claimed items, mark as distributed), live stock updates, form
validation, offline caching and the last 10 searches.

**Spec:** FR-USER-B-4–15 · FR-USER-P-4–7, P-9 (screens) · NFR-USER-R-1, R-4, R-5 ·
NFR-USER-PERS-1

## Role 5 — QA, DevOps & Documentation (Denver C. Balunatse)

**Owns:** CI (`.github/workflows/ci.yml`), deployment (Vercel, Render including the Celery
worker, Supabase, Upstash), test cases TC-01–56 and the traceability matrix, the Postman
collection, integration tests (including the two-buyers-one-item and two-partners-one-donation
races), Playwright tests for all four roles, usability and acceptance sessions, the use case,
activity, ERD and DFD diagrams, the README, terms of service and privacy pages (including
partner and donation terms and how delivery addresses are handled), the backup and
disaster-recovery write-up, and bug triage.

**Spec:** NFR-SYS-M-1–4 · NFR-SYS-A-1, A-2 · NFR-BUS-LC-1–5
