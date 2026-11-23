# Backup and Disaster Recovery Plan (NFR-SYS-A)

## 1. Recovery Objectives
In accordance with **NFR-SYS-A-1 through NFR-SYS-A-3** and **FR-SYS-11**:
- **Recovery Time Objective (RTO):** $\le 4\text{ hours}$ (maximum allowable downtime to restore full marketplace and API service).
- **Recovery Point Objective (RPO):** $\le 1\text{ hour}$ (maximum acceptable data loss window for orders, inventory, and user records).
- **Target Availability:** $99\%$ monthly uptime ($\le 7.2\text{ hours}$ downtime/month, **NFR-SYS-R-1**).

## 2. Backup Strategy by Layer

| Layer / Service | Data Stored | Backup Mechanism | Frequency & Retention |
| :--- | :--- | :--- | :--- |
| **Supabase PostgreSQL** | Users, profiles, listings, orders, payments, reviews, audit logs | Automated logical/physical database snapshots & Point-in-Time Recovery (PITR) | **Target:** Every 6 hours + WAL archiving for $\le 1\text{ hr}$ RPO, replicated to geographically separate storage.<br>**Free-Tier Prototype:** Daily automated Supabase backups + manual `pg_dump` exports before major migrations. |
| **Supabase Storage** | Seller product photos & partner accreditation files | Managed S3-compatible object storage with built-in redundancy | Continuous object durability; exported via storage bucket sync prior to demo milestones. |
| **Upstash Redis** | Live stock counters & Celery task queue | Ephemeral cache + persistent database source of truth | Rebuilt directly from PostgreSQL `quantity_available` values on cache miss or flush. |
| **Source Code & Config** | Frontend (Astro), Backend (FastAPI), Alembic migrations, CI workflows | Git version control on GitHub (`main` and `dev` protected branches) | Continuous distributed commits; environment templates tracked in `.env.example`. |

## 3. Disaster Recovery Procedures

### Scenario A: Database Corruption or Accidental Data Loss
1. **Assess & Isolate (0–30 mins):** Place backend in maintenance mode or pause write endpoints via Render environment configuration to halt further writes.
2. **Identify Recovery Point (30–60 mins):** Consult `audit_logs` and Supabase backup timestamps to select the latest clean snapshot or PITR timestamp within the $\le 1\text{ hour}$ RPO window.
3. **Restore Database (1–2.5 hours):**
   - Restore the snapshot in Supabase Dashboard (or run `pg_restore` onto a clean PostgreSQL instance).
   - Verify schema alignment against `backend/alembic/versions/`.
4. **Resync Cache & Verify (2.5–3.5 hours):** Flush stale Upstash Redis keys so live stock counters re-hydrate from PostgreSQL, then run `/api/health` and smoke tests (`TC-05`, `TC-19`, `TC-24`).
5. **Resume Traffic (< 4 hours RTO):** Re-enable frontend/backend traffic and notify affected users if any recent transactions fell inside the RPO window.

### Scenario B: Backend / Worker Hosting Outage (Render)
1. **Failover / Redeploy (0–1 hour):** Trigger a manual redeploy from the protected `main` branch in Render for both the FastAPI web service and the Celery worker (`render.yaml`).
2. **Alternate Host Recovery (1–3 hours):** Because the FastAPI backend and Celery worker are stateless and containerized/portable, spin up replacement instances on a secondary provider pointing to the existing Supabase `DATABASE_URL` and Upstash `REDIS_URL`.

### Scenario C: Frontend Hosting Outage (Vercel)
1. **Rollback or Redeploy (0–30 mins):** Promote the previous known-good deployment in Vercel or rebuild from `main` with `PUBLIC_API_BASE_URL` configured.

## 4. Verification & Testing
- Schema migrations (`alembic upgrade head`) and database seed/restore procedures are verified during pre-release staging checks (traced to **FR-SYS-11**).