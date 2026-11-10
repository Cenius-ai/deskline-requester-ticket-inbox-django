"""Server-side access control helpers.

Every protected view derives identity from the session and re-checks the role on
the server; templates only hide controls as a convenience.
"""

from functools import wraps

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Ticket, is_agent


def redirect_to_sign_in(request):
    sign_in_url = reverse("sign_in")
    next_url = request.get_full_path()
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(f"{sign_in_url}?next={next_url}")
    return redirect(sign_in_url)


def agent_required(view):
    """Agents only. Requesters are bounced to their portal, never to agent data."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_sign_in(request)
        if not is_agent(request.user):
            return redirect("portal")
        return view(request, *args, **kwargs)

    return wrapper


def requester_required(view):
    """Requesters only. Agents get sent to the inbox."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_sign_in(request)
        if is_agent(request.user):
            return redirect("inbox")
        return view(request, *args, **kwargs)

    return wrapper


def get_visible_ticket(user, pk):
    """Fetch a ticket the caller may see, or raise Http404.

    Agents see everything; requesters only their own tickets — another
    requester's ticket id is indistinguishable from a missing one.
    """
    queryset = Ticket.objects.select_related("requester", "assignee")
    if is_agent(user):
        ticket = queryset.filter(pk=pk).first()
    else:
        ticket = queryset.filter(pk=pk, requester=user).first()
    if ticket is None:
        raise Http404("Ticket not found")
    return ticket
