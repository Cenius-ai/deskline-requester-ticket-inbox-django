"""Domain model for Deskline: profiles, tickets, messages and macros."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()

ROLE_AGENT = "agent"
ROLE_REQUESTER = "requester"
ROLE_CHOICES = [(ROLE_AGENT, "Agent"), (ROLE_REQUESTER, "Requester")]


class Profile(models.Model):
    """Role for a Django user: support agent or the requester who wrote in."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_REQUESTER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"


def role_for(user):
    """Return 'agent' or 'requester' without creating rows or raising."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    cached = getattr(user, "_deskline_role", None)
    if cached:
        return cached
    try:
        role = user.profile.role
    except Profile.DoesNotExist:
        role = ROLE_AGENT if user.is_superuser else ROLE_REQUESTER
    user._deskline_role = role
    return role


def is_agent(user):
    return role_for(user) == ROLE_AGENT


def display_name(user):
    if user is None:
        return "Unassigned"
    full = user.get_full_name().strip()
    return full or user.get_username()


class Macro(models.Model):
    """A canned reply plus the status it moves the ticket to."""

    STATUS_CHOICES = [
        ("open", "Open"),
        ("pending", "Pending"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=120, unique=True)
    body = models.TextField()
    set_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    position = models.PositiveIntegerField(default=0, help_text="Order shown in the macro picker")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_OPEN = "open"
    STATUS_PENDING = "pending"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_PENDING, "Pending"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]
    OPEN_STATUSES = (STATUS_OPEN, STATUS_PENDING)

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_URGENT, "Urgent"),
    ]

    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL, db_index=True
    )
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="requested_tickets"
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
        null=True,
        blank=True,
    )
    sla_due_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "priority", "sla_due_at"])]

    def __str__(self):
        return f"#{self.pk} {self.subject}"

    @property
    def requester_name(self):
        return display_name(self.requester)

    @property
    def assignee_name(self):
        if self.assignee_id is None:
            return "Unassigned"
        return display_name(self.assignee)

    @property
    def is_open_state(self):
        return self.status in self.OPEN_STATUSES

    def save(self, *args, **kwargs):
        if not self.sla_due_at:
            from django.conf import settings

            self.sla_due_at = timezone.now() + timedelta(hours=settings.SLA_WINDOW_HOURS)
        super().save(*args, **kwargs)


class Message(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ticket_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Message #{self.pk} on ticket #{self.ticket_id}"

    @property
    def author_name(self):
        return display_name(self.author)

    @property
    def author_role(self):
        return role_for(self.author) or ROLE_REQUESTER
