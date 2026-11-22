# Frontend requirements coverage

How the frontend meets the user-facing non-functional requirements in
the SecondServe IT 313 document (NFR-USER-U-1 to U-10 and NFR-USER-PERS-3).
The table numbers changed in v13, so requirements are referred to by ID only. "Partly" means the frontend side is done and the rest
depends on the backend or on testing that can't be done in a browser
emulator.

| ID | Requirement | Status | Where and how |
| --- | --- | --- | --- |
| NFR-USER-U-1 | Ease of product listing (wizard) | Met | `/seller/add-listing` is a four-step wizard (food, price, pickup, review) with a progress bar, a live price preview, tips on every field that needs one, and a final review before publishing. Each step is checked before moving on. |
| NFR-USER-U-2 | Intuitive navigation (2–3 clicks) | Met | Every key action is one click from the sidebar or one more from the screen it starts on: register (sign-in → Register), search (Shop), list a product (Add Listing), purchase (Shop → Details → Add to cart → Reserve), view orders (My Pending Orders, My Order History). The sidebar is the same on every page of a role. |
| NFR-USER-U-3 | Clear pricing display | Met | The original price is struck through, the discount % is in a brick badge and "You save ₱…" is shown on listing cards, today's pick, the listing detail page, the cart (per line and in total) and the compare table. |
| NFR-USER-U-4 | Mobile responsiveness | Partly | Every screen was checked at 320, 768, 1024, 1440 and 2560px: no sideways page scrolling, and no button, filter, stepper or field under 44×44px. Below 1000px the menu is a drawer. Not yet tested on real iOS and Android devices. |
| NFR-USER-U-5 | WCAG 2.1 AA | Met, one risk | Text contrast is at least 4.5:1 in both themes; every control works from the keyboard with a visible focus ring; dialogs and the menu drawer manage focus; changes are announced through a live region; every photo has alt text; every field has a linked label and linked error. Risk: text fields are marked by a tinted fill without a border, which some auditors read as failing 1.4.11 (non-text contrast). Not yet tested with a real screen reader. |
| NFR-USER-U-6 | Load time | Partly | Pages are static HTML; photos are lazy-loaded, served at 480px for cards (about 25 KB each) and 960px only for large views, as progressive JPEGs with width and height set so nothing jumps; the first visible photo loads at high priority. The 2-second / 4G target has not been measured on a real network. |
| NFR-USER-U-7 | Consistent UI/UX | Met | One set of tokens in `global.css` (colours, type, spacing, radii, motion), one button system, one sidebar per role, the same page header on every screen, and the same words for the same things. |
| NFR-USER-U-8 | Error messages | Met | Form errors appear under the field in plain language and say how to fix it ("Make the discounted price lower than the original price of ₱120.00"); the first one takes focus. Server errors are explained by cause (offline, signed out, not allowed, gone, server problem) with what to do next, shown on screen and read out. |
| NFR-USER-U-9 | Help and support | Met | Info buttons beside fields open short explanations on Add Listing, Register and Shop Profile; Add Listing links to the seller help page; every role has a searchable Help & FAQ with seller-specific answers. |
| NFR-USER-U-10 | Visual feedback | Met | Buttons respond to hover and press; a button waiting on the server shows a spinner and can't be pressed twice; forms show their result on screen; pages cross-fade where the browser supports it. |
| NFR-USER-PERS-3 | Seller profile customisation | Met | `/seller/shop-profile` (in the seller menu and linked from Overview) edits the logo, shop name, area, description and up to four category tags, with a live preview. Buyers see it on each listing's detail page. Saving uses `GET/PATCH /me` (shop details inside `sellerProfile`); the logo upload route is still to be added on the backend. |

## Other user requirements

These are outside the frontend role's spec IDs but touch the frontend:

- NFR-USER-R-1 (real-time validation): fields re-check as you type once an
  error has shown; "already exists" checks need the backend.
- NFR-USER-R-2 (confirmation): publishing a listing and saving a profile
  confirm on screen; the email confirmation is a backend task.
- NFR-USER-PERS-1/2, R-3/4/5 and PERF-1/2/3 are not started.

## Still to cover after the partner and delivery changes

Decisions #10–12 in `DECISIONS.md` add screens these requirements now apply to:

- NFR-USER-U-1: the Add Listing wizard's pickup step becomes a fulfillment step
  (pickup, delivery or both, plus a delivery fee).
- NFR-USER-U-2: the partner role needs its own sidebar, with the Surplus Board,
  claimed items and distribution history each one click away.
- NFR-USER-U-3: delivery fees must appear in the cart and checkout totals.
- NFR-USER-U-4, U-5, U-8 and U-10: apply to the new checkout choice, delivery
  status and partner screens once they exist.
