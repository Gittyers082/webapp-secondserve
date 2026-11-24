# Working on Hapag

## Repo layout

```
/            Astro frontend (src/, public/) — deploys to Vercel
/backend     FastAPI API — deploys to Render (see backend/README.md)
/docs        decisions, roles, diagrams
```

## Branches

- `main` is what's deployed. Nobody pushes to it directly.
- `dev` is where finished features meet. PRs go into `dev`.
- Your work goes on a branch from `dev`, named for the role area and the feature:

  ```
  feat/be-listing-images      (backend)
  feat/fe-cart-checkout       (frontend)
  fix/be-order-double-book
  docs/update-erd
  ```

When `dev` is stable and demo-ready, the project lead merges `dev` into `main`.

## Daily flow

```bash
git checkout dev
git pull
git checkout -b feat/be-your-thing
# ...work, commit often...
git push -u origin feat/be-your-thing
# open a PR into dev on GitHub
```

## Commits (NFR-SYS-M-4)

Short, present tense, says what changed:

```
Add image upload for listings
Fix stock going negative when two buyers reserve at once
```

Not: `update`, `fix`, `asdf`, `hell yeah`.

## Pull requests

- One feature per PR. Small PRs get reviewed faster.
- CI (lint, type check, tests) must pass.
- At least one review before merging:
  - Backend PRs → Project Lead
  - Frontend PRs → Head Frontend
- In the description, say what it does, how you tested it, and which spec IDs it covers
  (e.g. `FR-USER-S-4`).

## Rules

- Never commit `.env` files, passwords or API keys. Use `.env.example` for the variable names.
- Write a test for every backend rule you add.
- Changing a database model? Generate a migration (`alembic revision --autogenerate`) in the same PR.
- Changing an API response? Update `src/api/client.ts` and `docs/api-contract.md` in the same PR, or tell Role 4.
- Search the code for `TODO(Role N)` to find tasks assigned to your role.
