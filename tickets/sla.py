"""SLA state and human labels, computed at render time from sla_due_at."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

STATE_ON_TRACK = "on_track"
STATE_DUE_SOON = "due_soon"
STATE_OVERDUE = "overdue"

STATE_LABELS = {
    STATE_ON_TRACK: "On track",
    STATE_DUE_SOON: "Due soon",
    STATE_OVERDUE: "Overdue",
}


def sla_due_soon_window():
    return timedelta(hours=settings.SLA_DUE_SOON_HOURS)


def sla_state(due_at, now=None):
    """'overdue', 'due_soon' or 'on_track' for a given SLA due time."""
    if due_at is None:
        return STATE_ON_TRACK
    now = now or timezone.now()
    remaining = due_at - now
    if remaining <= timedelta(0):
        return STATE_OVERDUE
    if remaining <= sla_due_soon_window():
        return STATE_DUE_SOON
    return STATE_ON_TRACK


def _humanize_minutes(minutes):
    minutes = max(int(minutes), 0)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours and mins:
        return f"{hours}h {mins:02d}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def sla_label(due_at, now=None):
    """Readable countdown: '2h 15m left' or '3h overdue'."""
    if due_at is None:
        return "No SLA"
    now = now or timezone.now()
    seconds = (due_at - now).total_seconds()
    minutes = round(abs(seconds) / 60)
    if seconds <= 0:
        return f"{_humanize_minutes(minutes)} overdue"
    return f"{_humanize_minutes(minutes)} left"
