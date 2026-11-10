"""Forms for Deskline. All validation server-side; templates render errors inline."""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import ROLE_AGENT, Macro, Ticket

User = get_user_model()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def agent_users():
    return User.objects.filter(profile__role=ROLE_AGENT, is_active=True).order_by(
        "first_name", "username"
    )


class SignInForm(forms.Form):
    """Accepts a username OR an email address (both are documented demo paths)."""

    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": "autofocus",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "cenius",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def resolve_user(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if not identifier:
            return None
        return (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
        )


class SignUpForm(forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=30,
        help_text="3–30 characters: letters, numbers, dot, dash or underscore.",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "e.g. jo.nakamura",
            }
        ),
    )
    email = forms.EmailField(
        label="Email (optional)",
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "id": "id_password1"}),
        help_text="At least 8 characters. Avoid common passwords.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not USERNAME_RE.match(username):
            raise ValidationError(
                "Use 3–30 letters, numbers, dots, dashes or underscores (no spaces)."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        elif password1:
            try:
                validate_password(password1, user=User(username=cleaned.get("username", "")))
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class NewTicketForm(forms.ModelForm):
    """Requester-facing create form: priority defaults to Normal."""

    class Meta:
        model = Ticket
        fields = ["subject", "description", "priority"]
        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "placeholder": "Short summary, e.g. “Invoice export is missing March”",
                    "autofocus": "autofocus",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "What happened, what you expected, and anything you already tried.",
                }
            ),
        }
        labels = {
            "subject": "Subject",
            "description": "Describe the issue",
            "priority": "Priority",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["priority"].choices = Ticket.PRIORITY_CHOICES
        self.fields["priority"].initial = Ticket.PRIORITY_NORMAL

    def clean_subject(self):
        subject = (self.cleaned_data.get("subject") or "").strip()
        if len(subject) < 4:
            raise forms.ValidationError("Give the ticket a subject of at least 4 characters.")
        return subject

    def clean_description(self):
        description = (self.cleaned_data.get("description") or "").strip()
        if len(description) < 10:
            raise forms.ValidationError(
                "Add a little more detail (at least 10 characters) so an agent can help."
            )
        return description


class ReplyForm(forms.Form):
    body = forms.CharField(
        label="Reply",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Write your reply…",
            }
        ),
    )

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Write something before sending.")
        return body


class TicketUpdateForm(forms.Form):
    """Agent-only: change status, priority and assignee in one POST."""

    status = forms.ChoiceField(choices=Ticket.STATUS_CHOICES)
    priority = forms.ChoiceField(choices=Ticket.PRIORITY_CHOICES)
    assignee = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label="Unassigned",
        label="Assignee",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = agent_users()

    @classmethod
    def for_ticket(cls, ticket):
        return cls(
            initial={
                "status": ticket.status,
                "priority": ticket.priority,
                "assignee": ticket.assignee_id,
            }
        )


class MacroApplyForm(forms.Form):
    macro = forms.ModelChoiceField(queryset=Macro.objects.all(), required=True)
