# Hapag

> A place at the table for everyone.

Frontend for Hapag (Tagalog for the dining table), formerly SecondServe. Any food
place can join: restaurants, carinderias, bakeries, cafes, groceries and caterers.
They list surplus food at a discount; buyers find it, reserve it, and collect it or
have it delivered; food that does not sell goes to partner charities and agencies as
donations. Built from the desktop wireframes with [Astro](https://astro.build) and
TypeScript.

This repository holds the **frontend only**. Every screen runs on typed seed data in
`src/data/`, so the whole flow is clickable before a server exists.

## Monorepo layout and team docs

This repo now holds both halves of Hapag:

| Folder | What | Deploys to |
| --- | --- | --- |
| `/` (this README) | Astro frontend | Vercel |
| [`backend/`](backend/README.md) | FastAPI API, database models, migrations | Render |
| [`docs/`](docs/) | [Decisions](docs/DECISIONS.md), [team roles](docs/ROLES.md) | — |

Start with [CONTRIBUTING.md](CONTRIBUTING.md) for branches, commits and PRs.
The frontend talks to the API through `src/api/client.ts`; copy `.env.example` to `.env`
and set `PUBLIC_API_BASE_URL`.

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
| `/`         | Redirects to sign-in                                    |
| `/login`    | Sign in; each role lands on its own dashboard           |
| `/register` | Create an account; sellers also give a business name    |

**Buyer**

| Route                  | Screen                                                              |
| ---------------------- | ------------------------------------------------------------------- |
| `/buyer/shop`          | Today's pick, photo categories, search, grid, selected item and cart |
| `/buyer/listing/:id`   | Listing detail: price and discount, pickup, shop reviews, reserve   |
| `/buyer/wishlist`      | Saved listings; choose up to three to compare                       |
| `/buyer/compare`       | Saved listings side by side (`?ids=` picks them)                    |
| `/buyer/cart`          | Cart grouped by shop, order summary, empty state                    |
| `/buyer/pending`       | Reserved and ready-for-pickup orders                                |
| `/buyer/history`       | Completed orders, write a review, clear history                     |
| `/buyer/notifications` | Notification centre                                                 |
| `/buyer/profile`       | Username and password, log out                                      |
| `/buyer/help`          | FAQ and who to ask                                                  |

**Seller**

| Route                   | Screen                                                     |
| ----------------------- | ---------------------------------------------------------- |
| `/seller`               | Overview: expiry stats and a 3-day filter                  |
| `/seller/analytics`     | Revenue, items rescued, savings, daily chart, top items    |
| `/seller/add-listing`   | Four-step listing wizard plus photo capture and upload     |
| `/seller/shop-profile`  | Public shop profile: logo, description, area, category tags |
| `/seller/listed-items`  | Read-only shelf                                            |
| `/seller/manage`        | Select a listing to edit, mark sold, withdraw or delete    |
| `/seller/handover`      | Reservations to hand over, and the completed order record  |
| `/seller/reviews`       | Average rating, rating breakdown and every review          |
| `/seller/notifications` | Notification centre                                        |
| `/seller/profile`       | Same profile screen as the buyer, labelled for sellers     |
| `/seller/help`          | FAQ and who to ask                                         |

**Administrator**

| Route                  | Screen                                         |
| ---------------------- | ---------------------------------------------- |
| `/admin`               | User management: search, filter, ban and unban |
| `/admin/approvals`     | Approve or decline new accounts                |
| `/admin/decisions`     | Record of every past decision                  |
| `/admin/moderation`    | Review listings, flag or remove them           |
| `/admin/sessions`      | Who is connected right now                     |
| `/admin/notifications` | Notification centre                            |
| `/admin/help`          | FAQ and who to ask                             |

## How it is put together

```
docs/
  api-contract.md          The API the frontend is built against, for the backend team
  requirements-coverage.md How each NFR-USER-U requirement and PERS-3 is met
public/
  brand/        hapag-mark.svg (the tile: a plate with an extra place set beside it),
                hapag-mark.png (512 px, favicon and app icon),
                hapag-logo.png (full square lockup with the tagline)
  photos/       Food photographs, one per listing type, with CREDITS.md
src/
  components/   Logo, Icon, Sidebar, ThemeToggle, FoodArt (listing photo), ListingCard,
                Stars, NotificationCenter, HelpCenter,
                QuantityStepper, Dialog, ProfilePanel
  api/          contract.ts (every endpoint, typed), client.ts (calls the server,
                or answers from seed data until one is configured)
  data/         types.ts (domain model), store.ts (seed data), nav.ts (sidebar
                items and their icons), icons.ts (icon names)
  layouts/      BaseLayout (window chrome), AppLayout (sidebar, main column and
                an optional summary rail), AuthLayout (split screen for connect,
                sign-in and register)
  pages/        One file per screen, grouped by role
  scripts/      Shared client behaviour: dialog (focus trap and restore),
                filters, selection, announce (screen-reader status),
                theme (light and dark), nav-drawer (menu below 1000px),
                wishlist, request (API calls from buttons, with errors shown),
                demo-forms (sign-in and profile stand-ins)
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
- **Accessible by default (WCAG 2.1 AA).** Text colours hold 4.5:1 on every
  surface they sit on. Every button, link-button, filter, stepper and field is
  at least 44 by 44px. Dialogs trap and restore focus, the menu drawer returns
  focus to its button, filter results and actions are announced through one
  polite status region, failed server calls are shown and announced, and every
  selectable card works from the keyboard. Motion respects
  `prefers-reduced-motion`.
- **Clear pricing.** Wherever a price is shown (cards, today's pick, listing
  detail, cart, compare) the original price is struck through, the discount
  percentage sits beside it in a brick badge, and the amount saved is spelled
  out.
- **Forms explain themselves.** Errors appear under the field in plain words
  and say how to fix them; info buttons beside fields open short explanations;
  buttons waiting on the server show a spinner. See
  `docs/requirements-coverage.md` for the full mapping to the spec.
- **No client framework.** Filtering, search, selection, steppers and dialogs are
  small TypeScript modules in `src/scripts/`, imported by each page's `<script>`
  block, so pages ship almost no JavaScript.
- **320px to 2560px.** Every screen is checked at 320, 768, 1024, 1440 and
  2560px with no sideways scrolling of the page. Above 1280px the sidebar shows
  labels; from 1000 to 1279px it folds to icons; below 1000px it becomes a
  drawer opened from a top bar, and the summary panel moves under the content.
  Data tables and the analytics chart scroll inside their own box on narrow
  screens. Above 2200px the app stays centred.
- **The look.** A dark working surface built from the brand's near-black ink,
  brick on actions and the active place, lime on counts and items that need
  attention, and the cream paper colour for text. Every signed-in screen has the
  same three parts: a sidebar with the role's sections, the main column, and,
  where a screen acts on one thing at a time, a summary rail on the right (the
  selected listing and cart on Shop, the order summary on View Cart, the
  selected listing's actions on Manage Listings and Item Moderation).
- **Glass, not outlines.** Panels, cards, the sidebar and dialogs are
  translucent and blur a slow wash of brand colour behind them. Nothing has a
  border: surfaces are told apart by tone, controls by a tinted fill. Only the
  keyboard focus ring draws a line. The wash stops moving when the system asks
  for reduced motion.
- **Light and dark.** A small round button beside the account name in the
  sidebar (and in the footer of the sign-in screens) switches themes. The
  choice is saved in the browser and applied by a small inline script in
  `BaseLayout` before the page paints, so a reload never flashes the other
  theme. Both themes are the same set of roles in `global.css`.
- **Spacing** uses one 4px-step scale (`--sp-1` to `--sp-16`), one gutter
  between sibling blocks and a wider step between sections.
- **Photos, not drawings.** `FoodArt.astro` shows an openly licensed photograph
  for each `FoodArt` key from `public/photos/`. They stand in for sellers' own
  uploads; `public/photos/CREDITS.md` lists each one's author and licence.
- **Icons** are drawn once in `Icon.astro` on a 24px grid with one stroke
  weight.
- **Branding** lives in `public/brand/`. `Logo.astro` takes a `variant`:
  `lockup` (mark plus wordmark — the app chrome and the sign-in screens),
  `mark` (the tile alone) or `full` (the square logo, wordmark included). The
  mark also serves as the favicon and the touch icon.

## Connecting it to a backend

The API the frontend expects is written down in `docs/api-contract.md` and typed
in `src/api/contract.ts`; please confirm or change it early.

Point the frontend at the API in a `.env` file at the project root:

```
PUBLIC_API_BASE_URL=http://localhost:8000/api
```

With it set, the seller and administrator actions (publish, edit, mark sold,
withdraw, delete, mark ready, ban, approve, flag, remove, refresh sessions) and
reviews and notifications go to the server through `src/api/client.ts`. Without
it, the same calls answer from the seed data in `src/data/store.ts`.

Still on seed data: the first render of every list (pages are built
statically), and the buyer's Shop, cart, checkout and wishlist, whose endpoints
are open questions in the contract. Sign-in, register and profile forms use
`src/scripts/demo-forms.ts`, which keeps field values out of the address bar.
