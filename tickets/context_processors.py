from django.conf import settings

from .models import role_for

NAV_BY_URL_NAME = {
    "inbox": "inbox",
    "inbox_slash": "inbox",
    "portal": "portal",
    "portal_slash": "portal",
    "portal_new": "new",
    "portal_new_slash": "new",
    "ticket_detail": "tickets",
    "ticket_detail_slash": "tickets",
}


def deskline_context(request):
    """Small, cheap values every template needs (product chrome + role)."""
    user = getattr(request, "user", None)
    signed_in = user is not None and user.is_authenticated
    role = role_for(user) if signed_in else None
    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else None
    return {
        "product_name": "Deskline",
        "product_tagline": "Requester Ticket Inbox",
        "current_role": role,
        "is_agent_user": role == "agent",
        "active_nav": NAV_BY_URL_NAME.get(url_name),
        "sla_window_hours": settings.SLA_WINDOW_HOURS,
        "sla_due_soon_hours": settings.SLA_DUE_SOON_HOURS,
        "demo_agent_identifier": settings.DEMO_AGENT_EMAIL,
        "demo_agent_username": settings.DEMO_AGENT_USERNAME,
        "demo_password": settings.DEMO_PASSWORD,
        "demo_requester_username": settings.DEMO_REQUESTER_USERNAME,
    }
