# Production Deployment

## Verified repository layout

This repository contains a FastAPI application at `app/main.py` and server-rendered Jinja templates under `app/templates`. The FastAPI object is named `app`. No React source, `package.json`, or frontend lockfile is present in this checkout, so there is no frontend build to deploy to Vercel yet.

Render builds from the root-level `Dockerfile` on the `main` branch. The container listens on Render's `PORT` (defaulting to `10000` for local container runs) and exposes the unauthenticated `/health` endpoint.

## Render environment variables

The Render Blueprint provisions a managed PostgreSQL database and passes its
connection string to the API via a `fromDatabase` reference. The API reads
`DATABASE_URL` (a `postgresql://` URL) and normalizes it to the
`postgresql+psycopg2` SQLAlchemy driver. When `DATABASE_URL` is unset (local
development), the API builds a PostgreSQL URL from `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

Set `CORS_ORIGINS` on the API service to the exact public origin only if the
browser frontend is hosted on a separate origin. This repository currently
serves its Jinja UI from the API itself, so same-origin browser requests do not
need CORS. Leave the origin list empty until a real separate frontend URL
exists; never use `*`.

Other API settings:

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | Generate a long random value; the Blueprint asks Render to generate one |
| `ENVIRONMENT` | `production` |
| `SESSION_COOKIE` | `warranty_session` |
| `SESSION_COOKIE_SAMESITE` | `none` for a separately hosted Vercel frontend |
| `SESSION_COOKIE_SECURE` | `true` |

`APP_NAME` is supplied by `render.yaml`. Do not put production values in `.env.example`, source code, or browser JavaScript. The app uses signed session cookies, not JWT. If a separate frontend is added later, configure its origin in `CORS_ORIGINS`; `SameSite=None; Secure` is needed for cross-site session cookies.

## Managed PostgreSQL

The Blueprint declares a Render managed PostgreSQL database (`warranty-postgres`)
in the same region as the API. Review current Render pricing in the dashboard
before creating it. The API service receives the database connection string
through a `fromDatabase` reference into `DATABASE_URL` and never embeds
credentials in this repository.

The app creates missing tables at startup with SQLAlchemy
`Base.metadata.create_all()`. This does not migrate existing columns and there
is no Alembic setup. Back up the PostgreSQL database using `pg_dump` before any
schema change. Use provider snapshots/backups and verify a restore.

## Schema changes and local-data import

The app currently calls SQLAlchemy `Base.metadata.create_all()` at startup. This creates missing tables but does not alter existing tables or delete rows. There is no migration framework in this repository. Before any production schema change, take a provider snapshot/backup, review the change, and apply an explicit forward migration (preferably introduce Alembic before ongoing schema evolution). Do not use table drops or destructive reinitialization against production.

## Vercel status

This checkout has no React app or frontend package manifest, so Vercel build/install/output settings and an SPA rewrite cannot be validated or safely created here. Once the actual frontend source is added or located, inspect its package scripts, lockfile, router, and API calls, then configure Vercel's Root Directory and its public API-origin variable accordingly.
