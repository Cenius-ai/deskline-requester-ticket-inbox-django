"""The shared ticket detail page plus reply / update / macro POST routes."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ReplyForm, TicketUpdateForm
from .models import Macro, Message, Ticket, is_agent
from .permissions import get_visible_ticket


def not_found(request):
    """A styled 404 that works even with DEBUG on (Django's debug page would leak)."""
    return render(request, "404.html", status=404)


def _visible_or_404(request, pk):
    try:
        return get_visible_ticket(request.user, pk), None
    except Http404:
        return None, not_found(request)


def _detail_context(request, ticket, reply_form=None, update_form=None):
    agent_view = is_agent(request.user)
    thread = list(ticket.messages.select_related("author"))
    context = {
        "ticket": ticket,
        "thread": thread,
        "message_count": len(thread),
        "reply_form": reply_form if reply_form is not None else ReplyForm(),
        "agent_view": agent_view,
        "reopens_on_reply": (not agent_view and ticket.status in (
            Ticket.STATUS_RESOLVED,
            Ticket.STATUS_CLOSED,
        )),
    }
    if agent_view:
        context["update_form"] = (
            update_form if update_form is not None else TicketUpdateForm.for_ticket(ticket)
        )
        context["macros"] = Macro.objects.all()
    return context


@login_required
@require_http_methods(["GET"])
def ticket_detail(request, pk):
    ticket, error = _visible_or_404(request, pk)
    if error:
        return error
    return render(request, "tickets/detail.html", _detail_context(request, ticket))


@login_required
@require_POST
def ticket_reply(request, pk):
    ticket, error = _visible_or_404(request, pk)
    if error:
        return error

    form = ReplyForm(request.POST)
    if not form.is_valid():
        status = 400 if request.headers.get("x-requested-with") else 200
        return render(
            request,
            "tickets/detail.html",
            _detail_context(request, ticket, reply_form=form),
            status=status,
        )

    reopened = False
    with transaction.atomic():
        Message.objects.create(
            ticket=ticket, author=request.user, body=form.cleaned_data["body"]
        )
        if not is_agent(request.user) and ticket.status in (
            Ticket.STATUS_RESOLVED,
            Ticket.STATUS_CLOSED,
        ):
            ticket.status = Ticket.STATUS_OPEN
            reopened = True
        ticket.save(update_fields=["status", "updated_at"])

    if reopened:
        messages.success(
            request, "Reply sent — the ticket is Open again so an agent picks it up."
        )
    else:
        messages.success(request, "Reply added to the thread.")
    return redirect("ticket_detail", pk=ticket.pk)


@login_required
@require_POST
def ticket_update(request, pk):
    ticket, error = _visible_or_404(request, pk)
    if error:
        return error
    if not is_agent(request.user):
        messages.error(request, "Only support agents can change a ticket's fields.")
        return redirect("ticket_detail", pk=ticket.pk)

    form = TicketUpdateForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "tickets/detail.html",
            _detail_context(request, ticket, update_form=form),
            status=400,
        )

    previous = f"{ticket.get_status_display()} · {ticket.get_priority_display()} · {ticket.assignee_name}"
    ticket.status = form.cleaned_data["status"]
    ticket.priority = form.cleaned_data["priority"]
    ticket.assignee = form.cleaned_data["assignee"]
    ticket.save(update_fields=["status", "priority", "assignee", "updated_at"])
    new = f"{ticket.get_status_display()} · {ticket.get_priority_display()} · {ticket.assignee_name}"
    messages.success(request, f"Ticket updated — now {new}." if previous != new else "No changes to save.")
    return redirect("ticket_detail", pk=ticket.pk)


@login_required
@require_http_methods(["GET", "POST"])
def ticket_delete(request, pk):
    """Agent-only delete: GET asks for confirmation, POST removes the ticket."""
    ticket, error = _visible_or_404(request, pk)
    if error:
        return error
    if not is_agent(request.user):
        messages.error(request, "Only support agents can delete a ticket.")
        return redirect("ticket_detail", pk=ticket.pk)

    if request.method == "POST":
        ticket_id = ticket.pk
        subject = ticket.subject
        ticket.delete()
        messages.success(request, f"Ticket #{ticket_id} “{subject}” was deleted.")
        return redirect("inbox")

    return render(
        request,
        "tickets/delete.html",
        {"ticket": ticket, "message_count": ticket.messages.count()},
    )


@login_required
@require_POST
def ticket_macro(request, pk):
    ticket, error = _visible_or_404(request, pk)
    if error:
        return error
    if not is_agent(request.user):
        messages.error(request, "Only support agents can apply macros.")
        return redirect("ticket_detail", pk=ticket.pk)

    macro = Macro.objects.filter(pk=request.POST.get("macro_id")).first()
    if macro is None:
        messages.error(request, "That macro is no longer available. Pick another one.")
        return redirect("ticket_detail", pk=ticket.pk)

    with transaction.atomic():
        Message.objects.create(ticket=ticket, author=request.user, body=macro.body)
        ticket.status = macro.set_status
        ticket.save(update_fields=["status", "updated_at"])

    messages.success(
        request,
        f"Applied macro “{macro.name}” — status set to {macro.get_set_status_display()}.",
    )
    return redirect("ticket_detail", pk=ticket.pk)
