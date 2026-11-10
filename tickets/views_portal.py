"""Requester portal: my tickets and the new-ticket form."""

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import NewTicketForm
from .models import Ticket
from .permissions import requester_required


def portal_summary(tickets):
    """KPI counts for the requester's own tickets."""
    now = timezone.now()
    return tickets.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status=Ticket.STATUS_OPEN)),
        pending=Count("id", filter=Q(status=Ticket.STATUS_PENDING)),
        resolved=Count("id", filter=Q(status=Ticket.STATUS_RESOLVED)),
        overdue=Count(
            "id",
            filter=Q(status__in=Ticket.OPEN_STATUSES, sla_due_at__lt=now),
        ),
    )


@requester_required
def portal(request):
    tickets = Ticket.objects.filter(requester=request.user).select_related("assignee")
    return render(
        request,
        "portal/list.html",
        {
            "tickets": tickets.order_by("-created_at", "-id"),
            "summary": portal_summary(tickets),
        },
    )


@requester_required
@require_http_methods(["GET", "POST"])
def portal_new(request):
    form = NewTicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.requester = request.user
        ticket.status = Ticket.STATUS_OPEN
        ticket.assignee = None
        ticket.save()
        messages.success(
            request,
            f"Ticket #{ticket.pk} raised. An agent picks it up within "
            f"{settings.SLA_WINDOW_HOURS} hours.",
        )
        return redirect("ticket_detail", pk=ticket.pk)

    return render(request, "portal/new.html", {"form": form})
