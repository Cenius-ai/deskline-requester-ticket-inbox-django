# Using Deskline Requester Ticket Inbox

## Overview

This is **Deskline Requester Ticket Inbox** — an HTTP API + web UI. This document covers the surface area you can use, with copy-pasteable examples for each entry point. For setup, see `INSTALL.md`.

## Quickstart

After completing the install steps in `INSTALL.md`:

```bash
python manage.py runserver    # start the server
# in another terminal:
curl http://localhost:8000/
```

## Endpoints

Every endpoint below was extracted from the source by the route scanner (Next.js / FastAPI / Flask / Django / Express).

| Method | Path | Source file |
|--------|------|-------------|
| `GET` | `/` | `deskline/urls.py` |
| `GET` | `/accounts/login/` | `tickets/urls.py` |
| `GET` | `/accounts/logout/` | `tickets/urls.py` |
| `GET` | `/accounts/signup/` | `tickets/urls.py` |
| `GET` | `/admin/` | `deskline/urls.py` |
| `GET` | `/health/` | `tickets/urls.py` |
| `GET` | `/inbox` | `tickets/urls.py` |
| `GET` | `/inbox/` | `tickets/urls.py` |
| `GET` | `/login/` | `tickets/urls.py` |
| `GET` | `/portal` | `tickets/urls.py` |
| `GET` | `/portal/` | `tickets/urls.py` |
| `GET` | `/portal/tickets/new` | `tickets/urls.py` |
| `GET` | `/portal/tickets/new/` | `tickets/urls.py` |
| `GET` | `/tickets/:pk` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/delete` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/delete/` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/macro` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/reply` | `tickets/urls.py` |
| `GET` | `/tickets/:pk/update` | `tickets/urls.py` |

### curl examples

#### `GET /`

```bash
curl http://localhost:8000/
```

#### `GET /accounts/login/`

```bash
curl http://localhost:8000/accounts/login/
```

#### `GET /accounts/logout/`

```bash
curl http://localhost:8000/accounts/logout/
```

#### `GET /accounts/signup/`

```bash
curl http://localhost:8000/accounts/signup/
```

#### `GET /admin/`

```bash
curl http://localhost:8000/admin/
```

## Worked example

1. Boot the server (`python manage.py runserver`).
2. Hit a smoke-test endpoint:

```bash
curl -sS http://localhost:8000/
```

3. If you get a JSON / HTML response, the server is healthy. Inspect `.env` if it errors with an auth/config failure.

## Reference

### Entry points

_No explicit entry points declared in this project's manifests._

### Surface index (auto-extracted)

| Kind | Title | Source file |
|------|-------|-------------|
| route | `/` | `deskline/urls.py` |
| route | `/accounts/login/` | `tickets/urls.py` |
| route | `/accounts/logout/` | `tickets/urls.py` |
| route | `/accounts/signup/` | `tickets/urls.py` |
| route | `/admin/` | `deskline/urls.py` |
| route | `/health/` | `tickets/urls.py` |
| route | `/inbox` | `tickets/urls.py` |
| route | `/inbox/` | `tickets/urls.py` |
| route | `/login/` | `tickets/urls.py` |
| route | `/portal` | `tickets/urls.py` |
| route | `/portal/` | `tickets/urls.py` |
| route | `/portal/tickets/new` | `tickets/urls.py` |
| route | `/portal/tickets/new/` | `tickets/urls.py` |
| route | `/tickets/:pk` | `tickets/urls.py` |
| route | `/tickets/:pk/` | `tickets/urls.py` |
| route | `/tickets/:pk/delete` | `tickets/urls.py` |
| route | `/tickets/:pk/delete/` | `tickets/urls.py` |
| route | `/tickets/:pk/macro` | `tickets/urls.py` |
| route | `/tickets/:pk/reply` | `tickets/urls.py` |
| route | `/tickets/:pk/update` | `tickets/urls.py` |

## Next steps

- Read [INSTALL.md](./INSTALL.md) if anything in the Quickstart didn't work.
- Inspect `.env.example` for the full list of environment variables this project understands.
- See [README.md](./README.md) for the architecture diagram + feature list.
