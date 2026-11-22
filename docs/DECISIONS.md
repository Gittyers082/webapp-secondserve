# Project decisions

Changes from the prelim proposal (IT 313, SECONDServe). The IT 313 document (v13) has been updated to match.

| # | Decision | Replaces in the proposal | Why |
| --- | --- | --- | --- |
| 1 | **Frontend is Astro + TypeScript, plain CSS.** Small browser scripts for interactivity and live stock. | React.js + Vite + Tailwind (Section V, Architecture 1) | The screens are already built in Astro; rewriting them would waste finished work. |
| 2 | ~~**Three roles: buyer, seller, admin.**~~ Replaced by #10. | Two roles only (FR-SYS-1, Tables 2–3, use case diagram) | Objective 4 (admin dashboard) and FR-BUS-7 (seller verification) need an admin. |
| 3 | ~~**Pickup only.**~~ Replaced by #11. | Delivery address (FR-USER-B-1, B-2, B-11) | Was simpler, but Baguio's hilly streets make pickup-only impractical. |
| 4 | **Web app on Vercel (frontend) and Render (backend).** The "connect to server" host/port screen is dropped. | — | The proposal already plans for hosted deployment. |
| 5 | **Product photos in Supabase Storage.** | Cloudflare R2 (seller key focus flows) | One service for DB, auth and files; 1 GB free. |
| 6 | **Free-tier limits.** Load balancer, 500 concurrent users and 6-hourly cross-region backups are documented targets, not built. Supabase Auth hashes passwords. | NFR-SYS-P-2/3, NFR-SYS-A-1/3, NFR-SYS-S-1 (bcrypt) | Not achievable on free plans. |
| 7 | **Sellers and partners wait for admin approval.** Buyers are active at once. | — | FR-BUS-7, FR-USER-P-2. |
| 8 | **One order per listing.** A cart checkout creates one order per line. | — | Matches the ERD (Order → one Listing) and the seller's handover screen. |
| 9 | **Payments are simulated.** Pay on pickup, or simulated GCash/card. 7% commission recorded per order. | — | FR-SYS-8, FR-BUS-4. No real card data ever touches the system. |
| 10 | **Four roles: buyer, seller, partner, admin.** Partners are LGUs, government agencies, charities and shelters. Admin approves sellers and partners, bans users, moderates listings. | #2 | Technopreneurship feedback (Nov 22): unsold food should still reach people in need (SDG 12). FR-SYS-1, FR-USER-P-1–9, UC-13–18. |
| 11 | **Pickup or delivery.** Each order is pickup at the store or delivery through a partner courier (Lalamove, Grab, local riders). The courier hand-off is simulated in the prototype; live integration is future work. | #3 | Baguio's terrain makes pickup hard for many buyers. FR-SYS-13, FR-USER-S-12, B-1, B-2, B-11, B-12, FR-BUS-13. |
| 12 | **Surplus and donation flow.** Listings still unsold about 6 hours before expiry go to a partner Surplus Board. Sellers can also turn a listing into a donation (₱0) or a discounted partner offer. Agencies buy surplus (simulated payment); charities and shelters claim donations for free. All verified partners in the area are notified, and partners mark items as distributed for impact reports. | — | Professor's questions: what happens to leftovers, reach, agency visibility, donations. FR-SYS-14–15, FR-USER-S-13, FR-BUS-14, UC-13–15. |

## Data model changes from #10–12

- New `partner_profiles` table linked to `users` (organization name and type, contact person, address, accreditation proof, verified date).
- `listings`: per-listing fulfillment options (pickup, delivery, or both), delivery fee, and a channel (marketplace, partner offer, donation).
- `orders`: fulfillment type, order type (sale, partner purchase, donation), delivery address, fee and status, and a distribution status for partner orders.
