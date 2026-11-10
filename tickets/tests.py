"""Deskline test suite: auth, inbox, ticket detail, macros, portal and seed.

Runs with either `python manage.py test` or `pytest`.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tickets.models import ROLE_AGENT, ROLE_REQUESTER, Macro, Message, Profile, Ticket
from tickets.sla import (
    STATE_DUE_SOON,
    STATE_ON_TRACK,
    STATE_OVERDUE,
    sla_label,
    sla_state,
)

User = get_user_model()

# Demo credentials come from the seeded settings, never from a literal here.
DEMO_AGENT = {"username": settings.DEMO_AGENT_USERNAME, "password": settings.DEMO_PASSWORD}
DEMO_AGENT_EMAIL = {"username": settings.DEMO_AGENT_EMAIL, "password": settings.DEMO_PASSWORD}
DEMO_REQUESTER = {
    "username": settings.DEMO_REQUESTER_USERNAME,
    "password": settings.DEMO_PASSWORD,
}


def seeded():
    call_command("seed", verbosity=0)


def random_password():
    """Per-run throwaway password for test fixtures; nothing is hardcoded."""
    return secrets.token_urlsafe(18)


def make_agent(username="agent.one", password=None):
    user = User.objects.create_user(username=username, password=password or random_password())
    Profile.objects.create(user=user, role=ROLE_AGENT)
    return user


def make_requester(username="requester.one", password=None):
    user = User.objects.create_user(username=username, password=password or random_password())
    Profile.objects.create(user=user, role=ROLE_REQUESTER)
    return user


def make_ticket(requester, **kwargs):
    defaults = {
        "subject": "Printer will not connect",
        "description": "The office printer drops off the network every morning.",
        "sla_due_at": timezone.now() + timedelta(hours=6),
    }
    defaults.update(kwargs)
    return Ticket.objects.create(requester=requester, **defaults)


class SlaHelperTests(TestCase):
    def test_due_soon_inside_four_hours(self):
        due = timezone.now() + timedelta(hours=2, minutes=15)
        self.assertEqual(sla_state(due), STATE_DUE_SOON)
        self.assertTrue(sla_label(due).endswith("left"))
        self.assertIn("2h", sla_label(due))

    def test_overdue_reports_elapsed_time(self):
        due = timezone.now() - timedelta(hours=3, minutes=5)
        self.assertEqual(sla_state(due), STATE_OVERDUE)
        self.assertIn("overdue", sla_label(due))

    def test_far_future_is_on_track(self):
        due = timezone.now() + timedelta(hours=20)
        self.assertEqual(sla_state(due), STATE_ON_TRACK)

    def test_badge_renders_state_and_label(self):
        requester = make_requester()
        ticket = make_ticket(requester, sla_due_at=timezone.now() + timedelta(hours=2))
        agent = make_agent()
        self.client.force_login(agent)
        response = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertContains(response, "Due soon")
        self.assertContains(response, "left")
        self.assertContains(response, 'data-sla-due=')


class SeedCommandTests(TestCase):
    def test_seed_creates_the_full_demo_set(self):
        seeded()
        self.assertEqual(User.objects.count(), 9)
        self.assertEqual(Ticket.objects.count(), 12)
        self.assertEqual(Macro.objects.count(), 5)
        self.assertGreaterEqual(Message.objects.count(), 12)
        self.assertEqual(Profile.objects.get(user__username="cenius").role, ROLE_AGENT)
        self.assertEqual(Profile.objects.get(user__username="maya.chen").role, ROLE_REQUESTER)

    def test_seed_is_idempotent(self):
        seeded()
        counts = (
            User.objects.count(),
            Ticket.objects.count(),
            Message.objects.count(),
            Macro.objects.count(),
            Profile.objects.count(),
        )
        seeded()
        self.assertEqual(
            counts,
            (
                User.objects.count(),
                Ticket.objects.count(),
                Message.objects.count(),
                Macro.objects.count(),
                Profile.objects.count(),
            ),
        )

    def test_seeded_tickets_cover_every_status_priority_and_sla_state(self):
        seeded()
        now = timezone.now()
        self.assertEqual(
            set(Ticket.objects.values_list("status", flat=True)),
            {Ticket.STATUS_OPEN, Ticket.STATUS_PENDING, Ticket.STATUS_RESOLVED, Ticket.STATUS_CLOSED},
        )
        self.assertEqual(
            set(Ticket.objects.values_list("priority", flat=True)),
            {p for p, _ in Ticket.PRIORITY_CHOICES},
        )
        self.assertEqual(
            {sla_state(t.sla_due_at, now) for t in Ticket.objects.all()},
            {STATE_ON_TRACK, STATE_DUE_SOON, STATE_OVERDUE},
        )

    def test_macros_are_ordered_and_well_formed(self):
        seeded()
        macros = list(Macro.objects.all())
        positions = [macro.position for macro in macros]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), len(positions))
        allowed = {value for value, _ in Ticket.STATUS_CHOICES}
        for macro in macros:
            self.assertTrue(macro.name)
            self.assertTrue(macro.body)
            self.assertIn(macro.set_status, allowed)

    def test_seeded_demo_credentials_authenticate(self):
        seeded()
        self.assertTrue(self.client.login(**DEMO_AGENT))
        self.client.logout()
        self.assertTrue(self.client.login(**DEMO_REQUESTER))


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seeded()

    def setUp(self):
        cache.clear()

    def test_agent_login_lands_in_the_inbox(self):
        response = self.client.post(
            reverse("sign_in"), DEMO_AGENT
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("inbox"))
        self.assertEqual(self.client.get(reverse("inbox")).status_code, 200)

    def test_email_identifier_also_authenticates(self):
        response = self.client.post(
            reverse("sign_in"), DEMO_AGENT_EMAIL
        )
        self.assertEqual(response["Location"], reverse("inbox"))

    def test_requester_login_lands_in_the_portal(self):
        response = self.client.post(
            reverse("sign_in"), DEMO_REQUESTER
        )
        self.assertEqual(response["Location"], reverse("portal"))
        self.assertEqual(self.client.get(reverse("portal")).status_code, 200)

    def test_wrong_credentials_share_one_non_enumerating_message(self):
        wrong_password = self.client.post(
            reverse("sign_in"), {"username": "cenius", "password": "not-it"}
        )
        unknown_user = self.client.post(
            reverse("sign_in"), {"username": "nobody.here", "password": "not-it"}
        )
        for response in (wrong_password, unknown_user):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Those credentials didn&#x27;t work.")
        # the typed username survives the failed attempt
        self.assertContains(wrong_password, 'value="cenius"')

    def test_anonymous_visitors_are_sent_to_the_sign_in_page(self):
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("sign_in")))

    def test_logout_is_post_only_and_ends_the_session(self):
        self.client.login(**DEMO_AGENT)
        self.assertEqual(self.client.get(reverse("sign_out")).status_code, 405)
        response = self.client.post(reverse("sign_out"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse("inbox")).status_code, 302)

    def test_sign_up_creates_a_requester_and_signs_them_in(self):
        response = self.client.post(
            reverse("sign_up"),
            {
                "username": "jo.nakamura",
                "email": "jo@example.com",
                "password1": "troubleshoot-91",
                "password2": "troubleshoot-91",
            },
        )
        self.assertEqual(response["Location"], reverse("portal"))
        user = User.objects.get(username="jo.nakamura")
        self.assertEqual(user.profile.role, ROLE_REQUESTER)
        self.assertEqual(self.client.get(reverse("portal")).status_code, 200)

    def test_sign_up_rejects_duplicate_username_and_mismatched_passwords(self):
        response = self.client.post(
            reverse("sign_up"),
            {
                "username": "cenius",
                "password1": "troubleshoot-91",
                "password2": "troubleshoot-91",
            },
        )
        self.assertContains(response, "already taken")
        self.assertFalse(User.objects.filter(username="cenius").count() > 1)

        response = self.client.post(
            reverse("sign_up"),
            {
                "username": "brand.new",
                "password1": "troubleshoot-91",
                "password2": "troubleshoot-92",
            },
        )
        self.assertContains(response, "do not match")
        self.assertFalse(User.objects.filter(username="brand.new").exists())

    def test_sign_in_page_shows_the_demo_hint_and_toggle(self):
        response = self.client.get(reverse("sign_in"))
        self.assertContains(response, "Demo:")
        self.assertContains(response, "cenius@cenius.ai")
        self.assertContains(response, "data-reveal")
        self.assertContains(response, 'type="password"')

    def test_security_headers_are_sent(self):
        response = self.client.get(reverse("sign_in"))
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("script-src 'self'", response["Content-Security-Policy"])


class InboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seeded()
        cls.agent = User.objects.get(username="cenius")

    def setUp(self):
        self.client.force_login(self.agent)

    def test_inbox_renders_every_badge_column(self):
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoice export is missing March")
        self.assertContains(response, "Unassigned")
        self.assertContains(response, "Overdue")
        self.assertContains(response, "Due soon")
        self.assertContains(response, "On track")
        self.assertContains(response, "priority--urgent")
        self.assertContains(response, "status--resolved")

    def test_status_tab_filters_the_queue(self):
        response = self.client.get(reverse("inbox"), {"status": "open"})
        statuses = {ticket.status for ticket in response.context["tickets"]}
        self.assertEqual(statuses, {Ticket.STATUS_OPEN})
        self.assertNotContains(response, "Weekly digest email never arrives")
        self.assertEqual(response.context["active_status"], "open")

    def test_search_matches_subject_and_requester(self):
        by_subject = self.client.get(reverse("inbox"), {"q": "Safari"})
        self.assertEqual(
            [t.subject for t in by_subject.context["tickets"]],
            ["SSO login loop on Safari"],
        )
        by_requester = self.client.get(reverse("inbox"), {"q": "Priya"})
        self.assertTrue(by_requester.context["tickets"])
        self.assertTrue(
            all(t.requester.first_name == "Priya" for t in by_requester.context["tickets"])
        )

    def test_queue_order_is_status_then_priority_then_sla(self):
        response = self.client.get(reverse("inbox"))
        tickets = list(response.context["tickets"])
        status_rank = {"open": 0, "pending": 1, "resolved": 2, "closed": 3}
        priority_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        keys = [
            (status_rank[t.status], priority_rank[t.priority], t.sla_due_at) for t in tickets
        ]
        self.assertEqual(keys, sorted(keys))

    def test_filtered_empty_state_offers_a_way_back(self):
        response = self.client.get(reverse("inbox"), {"q": "no-such-ticket-anywhere"})
        self.assertContains(response, "No tickets match these filters")
        self.assertContains(response, "Clear filters")

    def test_requesters_cannot_reach_the_agent_inbox(self):
        self.client.force_login(User.objects.get(username="maya.chen"))
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("portal"))


class TicketDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seeded()
        cls.agent = User.objects.get(username="cenius")

    def setUp(self):
        self.client.force_login(self.agent)
        self.ticket = Ticket.objects.filter(subject="Invoice export is missing March").first()

    def test_thread_lists_messages_oldest_first(self):
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        thread = list(response.context["thread"])
        self.assertEqual(thread, sorted(thread, key=lambda message: (message.created_at, message.pk)))
        self.assertContains(response, "Adding detail: the March CSV")

    def test_reply_appends_a_message_and_bumps_updated_at(self):
        before = Ticket.objects.get(pk=self.ticket.pk).updated_at
        response = self.client.post(
            reverse("ticket_reply", args=[self.ticket.pk]),
            {"body": "Export job finished — the March CSV now has all 74 rows."},
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertGreaterEqual(ticket.updated_at, before)
        self.assertEqual(ticket.messages.last().author, self.agent)
        self.assertIn("all 74 rows", ticket.messages.last().body)
        detail = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertContains(detail, "all 74 rows")

    def test_blank_reply_shows_inline_error_and_creates_nothing(self):
        before = self.ticket.messages.count()
        response = self.client.post(
            reverse("ticket_reply", args=[self.ticket.pk]), {"body": "   "}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field__error")
        self.assertContains(response, "field--invalid")
        self.assertEqual(self.ticket.messages.count(), before)

    def test_agent_can_update_status_priority_and_assignee(self):
        dana = User.objects.get(username="dana.whitfield")
        response = self.client.post(
            reverse("ticket_update", args=[self.ticket.pk]),
            {"status": "resolved", "priority": "low", "assignee": dana.pk},
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertEqual(ticket.status, Ticket.STATUS_RESOLVED)
        self.assertEqual(ticket.priority, Ticket.PRIORITY_LOW)
        self.assertEqual(ticket.assignee, dana)

    def test_agent_can_unassign_a_ticket(self):
        self.client.post(
            reverse("ticket_update", args=[self.ticket.pk]),
            {"status": "open", "priority": "high", "assignee": ""},
        )
        ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertIsNone(ticket.assignee)
        self.assertEqual(ticket.assignee_name, "Unassigned")

    def test_invalid_status_is_rejected_and_changes_nothing(self):
        before = Ticket.objects.get(pk=self.ticket.pk)
        response = self.client.post(
            reverse("ticket_update", args=[self.ticket.pk]),
            {"status": "exploded", "priority": "high", "assignee": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Select a valid choice", status_code=400)
        ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertEqual(ticket.status, before.status)
        self.assertEqual(ticket.priority, before.priority)

    def test_macro_picker_lists_macros_in_position_order(self):
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        macros = list(response.context["macros"])
        self.assertEqual([m.position for m in macros], sorted(m.position for m in macros))
        for macro in macros:
            self.assertContains(response, macro.name)

    def test_applying_a_macro_posts_its_body_and_sets_status(self):
        macro = Macro.objects.get(name="Ask for reproduction steps")
        response = self.client.post(
            reverse("ticket_macro", args=[self.ticket.pk]), {"macro_id": macro.pk}
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertEqual(ticket.status, macro.set_status)
        self.assertEqual(ticket.messages.last().body, macro.body)
        self.assertEqual(ticket.messages.last().author, self.agent)
        detail = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertContains(detail, macro.name)

    def test_applying_the_same_macro_twice_appends_two_messages(self):
        macro = Macro.objects.get(name="Confirm fix and resolve")
        before = self.ticket.messages.count()
        self.client.post(reverse("ticket_macro", args=[self.ticket.pk]), {"macro_id": macro.pk})
        self.client.post(reverse("ticket_macro", args=[self.ticket.pk]), {"macro_id": macro.pk})
        self.assertEqual(
            Ticket.objects.get(pk=self.ticket.pk).messages.count(), before + 2
        )

    def test_unknown_macro_id_is_handled_gracefully(self):
        response = self.client.post(
            reverse("ticket_macro", args=[self.ticket.pk]), {"macro_id": 99999}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer available")

    def test_mutations_require_post(self):
        self.assertEqual(
            self.client.get(reverse("ticket_reply", args=[self.ticket.pk])).status_code, 405
        )
        self.assertEqual(
            self.client.get(reverse("ticket_update", args=[self.ticket.pk])).status_code, 405
        )


class RequesterPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seeded()
        cls.requester = User.objects.get(username="maya.chen")

    def setUp(self):
        self.client.force_login(self.requester)

    def test_portal_lists_only_the_callers_tickets(self):
        response = self.client.get(reverse("portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoice export is missing March")
        self.assertNotContains(response, "SSO login loop on Safari")

    def test_new_ticket_defaults_and_computed_sla(self):
        response = self.client.post(
            reverse("portal_new"),
            {
                "subject": "Cannot add a teammate",
                "description": "The invite button stays greyed out for our workspace owner.",
                "priority": "normal",
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(subject="Cannot add a teammate")
        self.assertEqual(ticket.requester, self.requester)
        self.assertEqual(ticket.status, Ticket.STATUS_OPEN)
        self.assertEqual(ticket.priority, Ticket.PRIORITY_NORMAL)
        self.assertIsNone(ticket.assignee)
        hours_out = (ticket.sla_due_at - timezone.now()).total_seconds() / 3600
        self.assertAlmostEqual(hours_out, 8, delta=0.2)
        # and it is the newest row on the portal list
        portal = self.client.get(reverse("portal"))
        self.assertEqual(portal.context["tickets"].first(), ticket)

    def test_blank_subject_is_rejected_and_creates_no_ticket(self):
        before = Ticket.objects.count()
        response = self.client.post(
            reverse("portal_new"),
            {"subject": "", "description": "Something is broken here.", "priority": "normal"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.count(), before)
        self.assertContains(response, "This field is required")

    def test_new_ticket_form_defaults_to_normal_priority(self):
        response = self.client.get(reverse("portal_new"))
        self.assertContains(response, 'value="normal" selected')

    def test_requester_cannot_read_another_requesters_ticket(self):
        other = Ticket.objects.filter(requester__username="priya.nair").first()
        response = self.client.get(reverse("ticket_detail", args=[other.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "That page isn’t here", status_code=404)

    def test_requester_detail_hides_agent_controls(self):
        mine = Ticket.objects.filter(requester=self.requester).first()
        response = self.client.get(reverse("ticket_detail", args=[mine.pk]))
        self.assertContains(response, "Add a reply")
        self.assertNotContains(response, "Triage")
        self.assertNotContains(response, "Macros")
        self.assertNotContains(response, "Danger zone")
        self.assertNotContains(response, "Delete ticket")

    def test_requester_cannot_change_ticket_fields(self):
        mine = Ticket.objects.filter(requester=self.requester).first()
        original_status = mine.status
        response = self.client.post(
            reverse("ticket_update", args=[mine.pk]),
            {"status": "closed", "priority": "low", "assignee": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.get(pk=mine.pk).status, original_status)

    def test_requester_cannot_apply_macros(self):
        mine = Ticket.objects.filter(requester=self.requester).first()
        macro = Macro.objects.first()
        before = mine.messages.count()
        self.client.post(reverse("ticket_macro", args=[mine.pk]), {"macro_id": macro.pk})
        self.assertEqual(Ticket.objects.get(pk=mine.pk).messages.count(), before)

    def test_requester_reply_reopens_a_resolved_ticket(self):
        resolved = Ticket.objects.filter(
            requester=self.requester, status=Ticket.STATUS_RESOLVED
        ).first()
        if resolved is None:
            resolved = make_ticket(
                self.requester, subject="Resolved sample", status=Ticket.STATUS_RESOLVED
            )
        response = self.client.post(
            reverse("ticket_reply", args=[resolved.pk]),
            {"body": "It happened again this morning — could you take another look?"},
        )
        self.assertEqual(response.status_code, 302)
        reopened = Ticket.objects.get(pk=resolved.pk)
        self.assertEqual(reopened.status, Ticket.STATUS_OPEN)
        self.assertEqual(reopened.messages.last().author, self.requester)

    def test_agent_detail_shows_agent_controls(self):
        self.client.force_login(User.objects.get(username="cenius"))
        ticket = Ticket.objects.first()
        response = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertContains(response, "Triage")
        self.assertContains(response, "Macros")
        self.assertContains(response, "Danger zone")
        self.assertContains(response, reverse("ticket_delete", args=[ticket.pk]))

    def test_anonymous_ticket_access_redirects_to_sign_in(self):
        self.client.logout()
        ticket = Ticket.objects.first()
        response = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("sign_in")))


class TicketDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seeded()
        cls.agent = User.objects.get(username="cenius")
        cls.requester = User.objects.get(username="maya.chen")

    def setUp(self):
        self.client.force_login(self.agent)
        self.ticket = Ticket.objects.filter(subject="Invoice export is missing March").first()

    def test_confirmation_page_names_the_ticket_and_warns(self):
        response = self.client.get(reverse("ticket_delete", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.subject)
        self.assertContains(response, "Delete ticket permanently")
        self.assertContains(response, "no undo")

    def test_agent_delete_removes_the_ticket_and_its_messages(self):
        pk = self.ticket.pk
        self.assertGreater(self.ticket.messages.count(), 0)
        response = self.client.post(reverse("ticket_delete", args=[pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(pk=pk).exists())
        self.assertEqual(Message.objects.filter(ticket_id=pk).count(), 0)
        self.assertContains(response, "was deleted")
        # the queue no longer links to the deleted ticket
        self.assertNotContains(response, f'href="{reverse("ticket_detail", args=[pk])}"')

    def test_requester_cannot_delete_their_own_ticket(self):
        own = Ticket.objects.filter(requester=self.requester).first()
        self.client.force_login(self.requester)
        response = self.client.get(reverse("ticket_delete", args=[own.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("ticket_detail", args=[own.pk]))
        self.client.post(reverse("ticket_delete", args=[own.pk]))
        self.assertTrue(Ticket.objects.filter(pk=own.pk).exists())

    def test_requester_cannot_delete_someone_elses_ticket(self):
        other = Ticket.objects.filter(requester__username="priya.nair").first()
        self.client.force_login(self.requester)
        response = self.client.post(reverse("ticket_delete", args=[other.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Ticket.objects.filter(pk=other.pk).exists())

    def test_anonymous_delete_redirects_to_sign_in(self):
        self.client.logout()
        response = self.client.get(reverse("ticket_delete", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("sign_in")))

    def test_delete_requires_csrf_protection(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.agent)
        response = client.post(reverse("ticket_delete", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Ticket.objects.filter(pk=self.ticket.pk).exists())


class RootAndShellTests(TestCase):
    def test_root_sends_anonymous_visitors_to_sign_in(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("sign_in"))

    def test_root_sends_agents_to_the_inbox(self):
        seeded()
        self.client.force_login(User.objects.get(username="cenius"))
        self.assertEqual(self.client.get("/")["Location"], reverse("inbox"))

    @override_settings(SLA_WINDOW_HOURS=8)
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_missing_ticket_returns_the_styled_404(self):
        seeded()
        self.client.force_login(User.objects.get(username="cenius"))
        response = self.client.get(reverse("ticket_detail", args=[99999]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "That page isn’t here", status_code=404)
