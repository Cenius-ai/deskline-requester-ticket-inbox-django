from django import template
from django.utils import timezone

from tickets.sla import STATE_LABELS, sla_label, sla_state

register = template.Library()


@register.inclusion_tag("partials/sla_badge.html")
def sla_badge(ticket):
    """Render the SLA pill for a ticket, with data the 60-second tick can reuse."""
    now = timezone.now()
    state = sla_state(ticket.sla_due_at, now)
    return {
        "state": state,
        "state_label": STATE_LABELS[state],
        "label": sla_label(ticket.sla_due_at, now),
        "due_iso": ticket.sla_due_at.isoformat() if ticket.sla_due_at else "",
    }


@register.filter
def initials(name):
    """'Maya Chen' -> 'MC'; used by the thread avatars."""
    parts = [part for part in str(name or "").replace(".", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
