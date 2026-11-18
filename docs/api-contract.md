# SecondServe API contract (proposal)

This is the API the frontend is built against. It is a proposal for the backend
team to confirm or change early, so neither side waits on the other. The same
endpoints are typed in `src/api/contract.ts`; the frontend calls them through
`src/api/client.ts`.

## Conventions

- Base URL comes from `PUBLIC_API_BASE_URL` (for example
  `http://192.168.1.20:5050/api`). Without it the frontend runs on seed data.
- JSON in and out. Sessions use a cookie (`credentials: include`).
- Errors return a status code and `{ "message": "…" }`. The frontend shows the
  message to the user, so write it for a person.
- Money is a number in pesos (`60` is ₱60.00). Dates are ISO local date-times
  (`2026-11-05T18:00`); labels such as "Tomorrow, 6:00 PM" are worked out on the
  server, in the shop's time zone, and sent as `expiryLabel`.
- Shapes (`Listing`, `Order`, `User`, `Review`, `AppNotification`,
  `SaleRecord`, …) are the TypeScript interfaces in `src/data/types.ts`.

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
| POST | `/seller/profile/logo` | multipart, field `logo` (PNG or JPG, up to 2 MB) | `{ logoUrl }` |

`ListingInput`: `name`, `description?`, `category`, `quantity`,
`originalPrice`, `discountedPrice` (must be lower), `expiresAt`,
`pickupLocation`, `photoId?` (from a photo upload endpoint still to be agreed).

## Buyer

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/reviews` | `{ orderId, rating (1-5), comment }` | `Review` |

Still to agree: listings for the Shop, cart, checkout, pending orders, order
history and the wishlist. The buyer screens read seed data for these today.

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
