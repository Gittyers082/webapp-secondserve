# SecondServe

> Good products deserve a second chance.

Desktop-app frontend for SecondServe, a surplus-food marketplace. Shops list food
that is nearing expiry at a discount; buyers find it, reserve it, and collect it in
person. Built from the desktop wireframes with [Astro](https://astro.build) and
TypeScript.

This repository holds the **frontend only**. Every screen runs on typed seed data in
`src/data/`, so the whole flow is clickable before a server exists.

## Running it

```bash
npm install
npm run dev
```

The dev server prints a local address, usually <http://localhost:4321>.

| Command           | What it does                              |
| ----------------- | ----------------------------------------- |
| `npm run dev`     | Start the dev server with hot reload      |
| `npm run build`   | Build the static site into `dist/`        |
| `npm run preview` | Serve the built site locally              |
| `npm run check`   | Type-check every `.astro` and `.ts` file  |

## Screens

**Entry**

| Route       | Screen                                                  |
| ----------- | ------------------------------------------------------- |
| `/`         | Connect to server — host and port, with a failure state |
| `/login`    | Sign in; each role lands on its own dashboard           |
| `/register` | Create an account; sellers also give a business name    |

**Buyer**

| Route            | Screen                                                       |
| ---------------- | ------------------------------------------------------------ |
| `/buyer/shop`    | Today's pick, category filters, search, grid, details dialog |
| `/buyer/cart`    | Cart grouped by shop, order summary, empty state             |
| `/buyer/pending` | Reserved and ready-for-pickup orders                         |
| `/buyer/history` | Completed orders, with a clear-history confirmation          |
| `/buyer/profile` | Username and password, log out                               |

**Seller**

| Route                   | Screen                                                     |
| ----------------------- | ---------------------------------------------------------- |
| `/seller`               | Overview: expiry stats and a 3-day filter                  |
| `/seller/add-listing`   | Listing form plus photo capture, upload and confirm states |
| `/seller/listed-items`  | Read-only shelf                                            |
| `/seller/manage`        | Select a listing to edit, mark sold, withdraw or delete    |
| `/seller/handover`      | Reservations to hand over, and the completed order record  |
| `/seller/profile`       | Same profile screen as the buyer, labelled for sellers     |

**Administrator**

| Route               | Screen                                                |
| ------------------- | ----------------------------------------------------- |
| `/admin`            | User management: search, filter, ban and unban        |
| `/admin/approvals`  | Approve or decline new accounts                       |
| `/admin/decisions`  | Record of every past decision                         |
| `/admin/moderation` | Review listings, flag or remove them                  |
| `/admin/sessions`   | Who is connected right now                            |

## How it is put together

```
src/
  components/   Logo, FoodArt, TopBar, StatusBar, ListingCard,
                QuantityStepper, Dialog, ProfilePanel
  data/         types.ts (domain model), store.ts (seed data), nav.ts (tab bars)
  layouts/      BaseLayout (window chrome), AppLayout (signed-in shell),
                AuthLayout (split hero for connect, sign-in, register)
  pages/        One file per screen, grouped by role
  styles/       global.css — design tokens and shared primitives
```

- **Types first.** `src/data/types.ts` mirrors the entity diagram from the
  wireframes: `User`, `Listing`, `Order`, plus the status unions each screen
  switches on. Seed data in `store.ts` is typed against it, so a wrong status or a
  missing field is a build error.
- **Plain CSS.** Design tokens live on `:root` in `global.css`; components carry
  scoped styles. No CSS framework.
- **No client framework.** Filtering, search, selection, steppers and dialogs are
  small TypeScript modules in each page's `<script>` block, so pages ship almost no
  JavaScript.
- **Illustrations are inline SVG** in `FoodArt.astro`, keyed by the `FoodArt`
  union, so there are no image assets to keep in sync.

## Connecting it to a backend

Swap the seed data in `src/data/store.ts` for calls to the API and keep the types in
`types.ts` as the contract. The forms currently use `GET` navigations as stand-ins
for the real submissions.
