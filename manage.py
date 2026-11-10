#!/usr/bin/env python3
"""Django's command-line utility for Deskline.

`runserver` self-heals: if the SQLite file has no schema yet it migrates, and if
the demo agent is missing it runs the idempotent seed command. That keeps a bare
fresh clone bootable with a single documented command.
"""

import os
import sys


def bootstrap_for_runserver():
    """Make sure the database exists, is migrated and carries demo data."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskline.settings")
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.db import connection

    table_names = set(connection.introspection.table_names())
    if "tickets_ticket" not in table_names:
        print("→ creating database schema (migrate)")
        call_command("migrate", interactive=False, verbosity=0)

    User = get_user_model()
    if not User.objects.filter(username="cenius").exists():
        print("→ seeding demo data")
        call_command("seed")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskline.settings")
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        # One process keeps the SQLite writes serialized and the boot log readable.
        if "--noreload" not in sys.argv:
            sys.argv.append("--noreload")
        bootstrap_for_runserver()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - Django is a hard requirement
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available "
            "on your PYTHONPATH environment variable? Did you forget to "
            "activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
