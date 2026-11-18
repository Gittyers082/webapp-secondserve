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
public/
  brand/        secondserve-logo.png (full square lockup),
                secondserve-mark.png (tray-and-hand tile, rounded)
src/
  components/   Logo, FoodArt, TopBar, StatusBar, ListingCard,
                QuantityStepper, Dialog, ProfilePanel
  data/         types.ts (domain model), store.ts (seed data), nav.ts (tab bars)
  layouts/      BaseLayout (window chrome), AppLayout (signed-in shell),
                AuthLayout (split hero for connect, sign-in, register)
  pages/        One file per screen, grouped by role
  scripts/      Shared client behaviour: dialog (focus trap and restore),
                filters, selection, announce (screen-reader status),
                demo-forms (form stand-ins until a server exists)
  styles/       global.css — design tokens and shared primitives
```

- **Types first.** `src/data/types.ts` mirrors the entity diagram from the
  wireframes: `User`, `Listing`, `Order`, plus the status unions each screen
  switches on. Seed data in `store.ts` is typed against it, so a wrong status or a
  missing field is a build error.
- **Plain CSS.** Design tokens live on `:root` in `global.css`: colours, a type
  scale with an 11px floor, motion durations and easing, radii and spacing.
  Shared patterns (listing grid, grid tile, action bar, tables, chips, filters)
  live there too; components and pages carry only their own scoped styles. No CSS
  framework.
- **Accessible by default.** Text colours hold WCAG AA contrast on every surface
  they sit on, control borders hold 3:1, dialogs trap and restore focus, filter
  results and row actions are announced through one polite status region, and
  every selectable card works from the keyboard. Motion respects
  `prefers-reduced-motion`.
- **No client framework.** Filtering, search, selection, steppers and dialogs are
  small TypeScript modules in `src/scripts/`, imported by each page's `<script>`
  block, so pages ship almost no JavaScript.
- **Breakpoints.** Screens are laid out for 1440px and checked down to 1024px.
  Below 1200px listing grids go to two columns; below 1100px side panels stack.
- **Illustrations are inline SVG** in `FoodArt.astro`, keyed by the `FoodArt`
  union, so there are no image assets to keep in sync.
- **Branding** lives in `public/brand/`. `Logo.astro` takes a `variant`:
  `lockup` (mark plus wordmark — the app chrome and the sign-in screens),
  `mark` (the tile alone) or `full` (the square logo, wordmark included). The
  mark also serves as the favicon and the touch icon.

## Connecting it to a backend

Swap the seed data in `src/data/store.ts` for calls to the API and keep the types in
`types.ts` as the contract. Forms are marked `data-demo-form` and handled by
`src/scripts/demo-forms.ts`, which stops the submission (so no field value, password
included, reaches the address bar) and moves to the next screen or shows a
confirmation. Replace that module with real submissions.
