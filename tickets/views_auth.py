"""Sign in, sign up and sign out — role-aware landing for both personas."""

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods

from .forms import SignInForm, SignUpForm
from .models import ROLE_REQUESTER, Profile, is_agent

# A small in-process throttle keeps credential guessing expensive on a
# single-process self-hosted install without adding a cache service.
LOGIN_FAILURE_LIMIT = 25
LOGIN_FAILURE_WINDOW_SECONDS = 300


def landing_url(user):
    return reverse("inbox") if is_agent(user) else reverse("portal")


def _throttle_key(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")
    return f"deskline-login-failures:{ip}"


def _is_throttled(request):
    return (cache.get(_throttle_key(request)) or 0) >= LOGIN_FAILURE_LIMIT


def _record_failure(request):
    key = _throttle_key(request)
    try:
        cache.add(key, 0, LOGIN_FAILURE_WINDOW_SECONDS)
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOGIN_FAILURE_WINDOW_SECONDS)


def _safe_next(request, fallback):
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return fallback


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if request.user.is_authenticated:
        return redirect(landing_url(request.user))

    form = SignInForm(request.POST or None)
    if request.method == "POST":
        if _is_throttled(request):
            form.add_error(
                None, "Too many sign-in attempts. Wait a few minutes and try again."
            )
        elif form.is_valid():
            candidate = form.resolve_user()
            account = None
            if candidate is not None:
                account = authenticate(
                    request,
                    username=candidate.get_username(),
                    password=form.cleaned_data["password"],
                )
            if account is None:
                _record_failure(request)
                form.add_error(None, "Those credentials didn't work.")
            else:
                cache.delete(_throttle_key(request))
                login(request, account)
                Profile.objects.get_or_create(
                    user=account, defaults={"role": ROLE_REQUESTER}
                )
                messages.success(request, f"Signed in as {account.get_username()}.")
                return redirect(_safe_next(request, landing_url(account)))

    return render(
        request,
        "auth/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@require_http_methods(["GET", "POST"])
def sign_up(request):
    if request.user.is_authenticated:
        return redirect(landing_url(request.user))

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            account = get_user_model().objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data.get("email") or "",
                password=form.cleaned_data["password1"],
            )
            Profile.objects.update_or_create(
                user=account, defaults={"role": ROLE_REQUESTER}
            )
        login(request, account, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            request, "Your requester account is ready. Raise your first ticket below."
        )
        return redirect("portal")

    return render(request, "auth/signup.html", {"form": form})


@require_POST
def sign_out(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("sign_in")
