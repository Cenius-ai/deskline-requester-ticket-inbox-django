# Installing Deskline

Deskline is a Django 5 application with SQLite. There is nothing to compile and no external
service to run.

## Prerequisites

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.11 or newer | `python3 --version` |
| pip | bundled with Python | `python3 -m pip --version` |
| SQLite | 3.35+ | bundled with CPython; no server needed |

No Node, no Docker, no database server, no system packages.

## Step 1 — install dependencies

```bash
python3 -m pip install -r requirements.txt
```

This installs Django (runtime) plus pytest and pytest-django (test runner only).

If you prefer a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Step 2 — create the database schema

```bash
python3 manage.py migrate
```

Creates `db.sqlite3` in the project root and applies the committed migrations. Safe to re-run.

## Step 3 — seed the demo data

```bash
python3 manage.py seed
```

Creates the two demo accounts, the five macros and twelve sample tickets with conversations and
SLA deadlines spread from overdue to comfortably on track. Idempotent: running it again changes
no counts. It prints a summary and exits — it never starts a web server.

## Step 4 — run Deskline

```bash
python3 manage.py runserver 0.0.0.0:8000
```

Open <http://localhost:8000>. Sign in with the demo accounts:

| Username | Email | Role | Password |
| --- | --- | --- | --- |
| `cenius` | cenius@cenius.ai | Agent | `cenius` |
| `maya.chen` | maya@fieldnote.studio | Requester | `cenius` |

(Remove or re-password these accounts before a production deploy.)

## One-command install

`install.sh` performs steps 1–3 and exits without starting a server:

```bash
sh install.sh
python3 manage.py runserver 0.0.0.0:8000
```

## Tests

```bash
python3 manage.py test
```

## Configuration (optional)

Deskline needs no environment variables to boot. To customise a deployment, export any of the
values documented in `.env.example` (Django reads them from the process environment; a `.env`
file is not loaded automatically).

## Production notes

- Run behind a reverse proxy and let it serve `/static/` from `staticfiles/` after
  `python3 manage.py collectstatic`; keep `DJANGO_DEBUG=false` in production.
- Set `DJANGO_SECRET_KEY` to a long random value.
- If you terminate TLS at the proxy, add `SECURE_SSL_REDIRECT` and secure-cookie settings for
  your deployment; the shipped defaults are HTTP-friendly on purpose.
- Back up `db.sqlite3` — it is the entire database.
