# SecondServe API contract (proposal)

This is the API the frontend is built against. It is a proposal for the backend
team to confirm or change early, so neither side waits on the other. The same
endpoints are typed in `src/api/contract.ts`; the frontend calls them through
`src/api/client.ts`.

## Conventions

- Base URL comes from `PUBLIC_API_BASE_URL` (for example
  `http://localhost:8000/api` locally, the Render URL in production). Without it the frontend runs on seed data.
- JSON in and out. Sessions use a cookie (`credentials: include`).
- Errors return a status code and `{ "message": "…" }`. The frontend shows the
  message to the user, so write it for a person.
- Money is a number in pesos (`60` is ₱60.00). Dates are ISO local date-times
  (`2026-11-05T18:00`); labels such as "Tomorrow, 6:00 PM" are worked out on the
  server, in the shop's time zone, and sent as `expiryLabel`.
- Shapes (`Listing`, `Order`, `User`, `Review`, `AppNotification`,
  `SaleRecord`, …) are the TypeScript interfaces in `src/data/types.ts`.

## Alignment with the backend

The backend's interactive docs (`http://localhost:8000/docs` while it runs) are the
source of truth for paths and shapes. Frontend paths are written without the `/api`
prefix, because `PUBLIC_API_BASE_URL` already ends in `/api`.

These are the paths this proposal used and what the backend serves instead.

### Seller

| Frontend called | Backend route | Notes |
| --- | --- | --- |
| `GET /seller/listings` | `GET /listings/mine` | |
| `POST /seller/listings` | `POST /listings` | |
| `PATCH /seller/listings/:id` | `PATCH /listings/:id` | |
| `POST /seller/listings/:id/status` | `POST /listings/:id/status` | |
| `DELETE /seller/listings/:id` | `DELETE /listings/:id` | |
| `GET /seller/orders` | `GET /orders/mine` | Sellers get the orders they received |
| `POST /seller/orders/:id/ready` | `POST /orders/:id/ready` | |
| `GET /seller/profile` | `GET /me` | Shop details are inside `sellerProfile`; the frontend maps them to `ShopProfile` |
| `PATCH /seller/profile` | `PATCH /me` | Shop fields go inside `{ seller: { ... } }` with the backend's field names |
| `POST /reviews` | `POST /orders/:orderId/review` | Body is `{ rating, comment }` |
| `GET /seller/reviews` | none yet | Backend to add (Role 1) |
| `POST /seller/profile/logo` | `POST /me/logo` | Done; the client now calls `/me/logo` |
| `GET /seller/sales` | none yet | Backend to add (Role 1) |

### Administrator

| Frontend called | Backend route | Notes |
| --- | --- | --- |
| `GET /admin/users` | same | |
| `POST /admin/users/:username/ban` | `POST /admin/users/:userId/ban` | By user id, not username |
| `POST /admin/users/:username/unban` | `POST /admin/users/:userId/unban` | By user id, not username |
| `GET /admin/approvals` | same | |
| `POST /admin/approvals/:id` | same | Returns the updated `User`, not an `AccountDecision` |
| `GET /admin/decisions` | same | |
| `GET /admin/listings` | same | Flagged first; filters `flagged`, `status`, `q`; each item has `flagReason` |
| `POST /admin/listings/:id/flag` | same | Optional body `{ reason }`; `POST .../unflag` clears it |
| `DELETE /admin/listings/:id` | same | Marks it `removed` (not deleted) and tells the seller; optional `{ reason }` |
| `GET /admin/sessions` | same | Returns `{ userId, username, role, lastSeenAt }[]` for the last 30 minutes; no IP address |
| none | `GET /admin/stats` | Platform totals for a dashboard |
| none | `GET /admin/export.csv?from=&to=` | Orders and payments as a CSV download |
| none | `GET /orders/:id/receipt` | Printable HTML receipt for the buyer, partner or seller |

### Everyone signed in

Notifications already match: `GET /notifications`, `POST /notifications/:id/read`,
`POST /notifications/read-all`.

## Seller

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/seller/listings` | | `Listing[]` |
| POST | `/seller/listings` | `ListingInput` | `Listing` |
| PATCH | `/seller/listings/:id` | partial `ListingInput` | `Listing` |
| POST | `/seller/listings/:id/status` | `{ status: "sold" \| "withdrawn" }` | `Listing` |
| DELETE | `/seller/listings/:id` | | 204 |
| GET | `/seller/orders` | | `Order[]` (reserved and ready) |
| POST | `/seller/orders/:id/ready` | | `Order` |
| GET | `/seller/sales?from=&to=` | | `SaleRecord[]` |
| GET | `/seller/reviews` | | `Review[]` |
| GET | `/seller/profile` | | `ShopProfile` |
| PATCH | `/seller/profile` | `{ shopName?, description?, tags?, location? }` | `ShopProfile` |
| POST | `/me/logo` | multipart, field `file` (JPEG, PNG or WebP, up to 2 MB) | `{ logoUrl }` |

`ListingInput`: `name`, `description?`, `category`, `quantity`,
`originalPrice`, `discountedPrice` (must be lower), `expiresAt`,
`pickupLocation`, `photoId?` (from a photo upload endpoint still to be agreed).

## Buyer

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/reviews` | `{ orderId, rating (1-5), comment }` | `Review` |

Still to agree: listings for the Shop, cart, checkout, pending orders, order
history and the wishlist. The buyer screens read seed data for these today.

## Partner

Partners are LGUs, government agencies, charities and shelters. An
administrator approves them before they can sign in.

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/partners/surplus` | | `{ items: Listing[], total, limit, offset }` |
| GET | `/partners/orders` | | `Order[]` |
| POST | `/partners/surplus/:id/buy` | `{ quantity, fulfillmentType, deliveryAddress? }` | `Order` |
| POST | `/partners/surplus/:id/claim` | `{ quantity, fulfillmentType, deliveryAddress? }` | `Order` |
| POST | `/partners/orders/:id/distributed` | | `Order` |
| POST | `/orders/:id/delivery` (seller) | `{ status: "out-for-delivery" \| "delivered" }` | `Order` |
| POST | `/listings/:id/offer-to-partners` (seller) | `{ channel: "partner-offer" \| "donation", partnerPrice? }` | `Listing` |

`fulfillmentType` is `"pickup"` or `"delivery"`; `deliveryAddress` is required
for delivery. The Surplus Board also takes `q`, `channel`, `category`,
`maxPrice`, `minQuantity`, `expiringSoon`, `expiresBefore` and `sort`. A
delivery goes `pending` → `preparing` (seller marks it ready) →
`out-for-delivery` → `delivered`. The partner screens are in
`src/pages/partner/` and call these through `api.partner` in
`src/api/client.ts`.

## Administrator

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/admin/users` | | `User[]` |
| POST | `/admin/users/:username/ban` | | `User` |
| POST | `/admin/users/:username/unban` | | `User` |
| GET | `/admin/approvals` | | `PendingAccount[]` |
| POST | `/admin/approvals/:id` | `{ decision: "approved" \| "declined" }` | `AccountDecision` |
| GET | `/admin/decisions` | | `AccountDecision[]` |
| GET | `/admin/listings` | | `Listing[]` |
| POST | `/admin/listings/:id/flag` | | `Listing` |
| DELETE | `/admin/listings/:id` | | 204 |
| GET | `/admin/sessions` | | `Session[]` |

## Everyone signed in

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/notifications` | | `AppNotification[]` |
| POST | `/notifications/:id/read` | | 204 |
| POST | `/notifications/read-all` | | 204 |

## Open questions for the backend team

1. Sign-in: the desktop app connects to a server address first. Is the session
   a cookie, or should the client send a token header?
2. Photo upload: multipart to `POST /photos` returning `{ photoId, url }`?
3. Pagination for long lists (users, order history): page and size, or a cursor?
4. Live updates (a reservation arriving, an order turning ready): polling, or a
   WebSocket the app can subscribe to?
