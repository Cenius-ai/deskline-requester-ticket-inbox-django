#!/usr/bin/env bash
# Deskline installer: dependencies -> migrations -> demo data. Then it EXITS.
# Runs unprivileged; uses only pip and Django's own management commands.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

echo "==> Deskline install: checking Python"
"$PYTHON" --version

echo "==> Deskline install: project dependencies"
# Best effort: some corporate images ship a pip that cannot upgrade itself.
"$PYTHON" -m pip install --upgrade pip setuptools wheel || \
  echo "    (warning: could not upgrade pip tooling; continuing with the installed pip)"
"$PYTHON" -m pip install -r requirements.txt

echo "==> Deskline install: database schema"
"$PYTHON" manage.py migrate --noinput

echo "==> Deskline install: demo data (idempotent)"
"$PYTHON" manage.py seed

echo "==> Deskline install: import self-check"
"$PYTHON" -c "import django, tickets, deskline; print('    Django', django.get_version(), 'ready')"

cat <<'DONE'

Deskline is installed. Start it with:

    python3 manage.py runserver 0.0.0.0:8000

Then open http://localhost:8000 and sign in as:
    agent      cenius@cenius.ai / cenius
    requester  maya.chen / cenius
DONE
