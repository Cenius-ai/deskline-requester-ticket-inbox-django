"""Agent-facing views: the shared inbox queue."""

from datetime import timedelta

from django.db.models import Case, Count, IntegerField, Q, When
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Ticket, is_agent
from .permissions import agent_required

STATUS_TABS = [
    ("all", "All"),
    (Ticket.STATUS_OPEN, "Open"),
    (Ticket.STATUS_PENDING, "Pending"),
    (Ticket.STATUS_RESOLVED, "Resolved"),
    (Ticket.STATUS_CLOSED, "Closed"),
]
STATUS_TAB_VALUES = {value for value, _ in STATUS_TABS}

# Queue order: open before pending before resolved before closed, then the most
# urgent priority, then whichever SLA falls due first. Deterministic by id last.
STATUS_RANK = Case(
    When(status=Ticket.STATUS_OPEN, then=0),
    When(status=Ticket.STATUS_PENDING, then=1),
    When(status=Ticket.STATUS_RESOLVED, then=2),
    When(status=Ticket.STATUS_CLOSED, then=3),
    default=4,
    output_field=IntegerField(),
)
PRIORITY_RANK = Case(
    When(priority=Ticket.PRIORITY_URGENT, then=0),
    When(priority=Ticket.PRIORITY_HIGH, then=1),
    When(priority=Ticket.PRIORITY_NORMAL, then=2),
    When(priority=Ticket.PRIORITY_LOW, then=3),
    default=4,
    output_field=IntegerField(),
)


def queue_summary(queryset=None):
    """Aggregate counts used by the KPI strip (real data, no invented deltas)."""
    queryset = queryset if queryset is not None else Ticket.objects.all()
    now = timezone.now()
    return queryset.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status=Ticket.STATUS_OPEN)),
        pending=Count("id", filter=Q(status=Ticket.STATUS_PENDING)),
        resolved=Count("id", filter=Q(status=Ticket.STATUS_RESOLVED)),
        closed=Count("id", filter=Q(status=Ticket.STATUS_CLOSED)),
        overdue=Count(
            "id",
            filter=Q(status__in=Ticket.OPEN_STATUSES, sla_due_at__lt=now),
        ),
        due_soon=Count(
            "id",
            filter=Q(
                status__in=Ticket.OPEN_STATUSES,
                sla_due_at__gte=now,
                sla_due_at__lte=now + timedelta(hours=4),
            ),
        ),
        unassigned=Count(
            "id",
            filter=Q(status__in=Ticket.OPEN_STATUSES, assignee__isnull=True),
        ),
    )


@agent_required
def inbox(request):
    active_status = request.GET.get("status", "all")
    if active_status not in STATUS_TAB_VALUES:
        active_status = "all"
    query = (request.GET.get("q") or "").strip()

    tickets = Ticket.objects.select_related("requester", "assignee")
    if active_status != "all":
        tickets = tickets.filter(status=active_status)
    if query:
        tickets = tickets.filter(
            Q(subject__icontains=query)
            | Q(description__icontains=query)
            | Q(requester__username__icontains=query)
            | Q(requester__first_name__icontains=query)
            | Q(requester__last_name__icontains=query)
        )

    tickets = tickets.annotate(
        status_rank=STATUS_RANK, priority_rank=PRIORITY_RANK
    ).order_by("status_rank", "priority_rank", "sla_due_at", "id")

    now = timezone.now()
    watchlist = (
        Ticket.objects.select_related("requester", "assignee")
        .filter(
            status__in=Ticket.OPEN_STATUSES,
            sla_due_at__lte=now + timedelta(hours=4),
        )
        .order_by("sla_due_at", "id")[:5]
    )

    context = {
        "tickets": tickets,
        "result_count": tickets.count(),
        "summary": queue_summary(),
        "status_tabs": STATUS_TABS,
        "active_status": active_status,
        "query": query,
        "watchlist": watchlist,
        "filters_active": active_status != "all" or bool(query),
        "unassigned_total": Ticket.objects.filter(
            status__in=Ticket.OPEN_STATUSES, assignee__isnull=True
        ).count(),
    }
    return render(request, "inbox/list.html", context)


def root(request):
    """GET / is the front door: send people to their own surface."""
    if not request.user.is_authenticated:
        return redirect("sign_in")
    return redirect("inbox" if is_agent(request.user) else "portal")


def health(request):
    """Trivial liveness probe for self-hosters and reverse proxies."""
    return HttpResponse("ok", content_type="text/plain")
