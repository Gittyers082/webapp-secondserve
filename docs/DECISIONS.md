# Project decisions

Changes from the prelim proposal (IT 313, SECONDServe). Update the proposal to match.

| # | Decision | Replaces in the proposal | Why |
| --- | --- | --- | --- |
| 1 | **Frontend is Astro + TypeScript, plain CSS.** Small browser scripts for interactivity and live stock. | React.js + Vite + Tailwind (Section V, Architecture 1) | The screens are already built in Astro; rewriting them would waste finished work. |
| 2 | **Three roles: buyer, seller, admin.** Admin approves sellers, bans users, moderates listings, sees platform stats. | Two roles only (FR-SYS-1, Tables 2–3, use case diagram) | Objective 4 (admin dashboard) and FR-BUS-7 (seller verification) need an admin. |
| 3 | **Pickup only.** Buyers reserve, then collect in person with a pickup code. | Delivery address (FR-USER-B-1, B-2, B-11) | Much simpler; fits small bakeries and shops. |
| 4 | **Web app on Vercel (frontend) and Render (backend).** The "connect to server" host/port screen is dropped. | — | The proposal already plans for hosted deployment. |
| 5 | **Product photos in Supabase Storage.** | Cloudflare R2 (seller key focus flows) | One service for DB, auth and files; 1 GB free. |
| 6 | **Free-tier limits.** Load balancer, 500 concurrent users and 6-hourly cross-region backups are documented targets, not built. Supabase Auth hashes passwords. | NFR-SYS-P-2/3, NFR-SYS-A-1/3, NFR-SYS-S-1 (bcrypt) | Not achievable on free plans. |
| 7 | **Sellers wait for admin approval before listing.** Buyers are active at once. | — | FR-BUS-7. |
| 8 | **One order per listing.** A cart checkout creates one order per line. | — | Matches the ERD (Order → one Listing) and the seller's handover screen. |
| 9 | **Payments are simulated.** Pay on pickup, or simulated GCash/card. 7% commission recorded per order. | — | FR-SYS-8, FR-BUS-4. No real card data ever touches the system. |

## Proposal sections to update

- Section V and III-A: React → Astro.
- Tables 1–3 and the use cases: add the admin role and its requirements.
- FR-USER-B-1, B-2, B-11: delivery address → pickup.
- ERD: add `role` (buyer/seller/admin) and `status` to User; pickup location and pickup code instead of delivery address; add Account Decision and Audit Log tables.
- Seller key focus flows: Cloudflare R2 → Supabase Storage.
