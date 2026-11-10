"""Idempotent demo data for Deskline.

Run `python manage.py seed` as often as you like: every row is looked up before
it is created, so a rerun duplicates nothing. The command never touches the
HTTP layer and exits as soon as the summary is printed.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tickets.models import ROLE_AGENT, ROLE_REQUESTER, Macro, Message, Profile, Ticket

User = get_user_model()

# (username, first, last, email, role, password-or-None)
PEOPLE = [
    ("cenius", "Casey", "Nius", "cenius@cenius.ai", ROLE_AGENT, "cenius"),
    ("dana.whitfield", "Dana", "Whitfield", "dana@deskline.local", ROLE_AGENT, None),
    ("omar.haddad", "Omar", "Haddad", "omar@deskline.local", ROLE_AGENT, None),
    ("maya.chen", "Maya", "Chen", "maya@fieldnote.studio", ROLE_REQUESTER, "cenius"),
    ("priya.nair", "Priya", "Nair", "priya@harbourline.co", ROLE_REQUESTER, None),
    ("tomas.oliveira", "Tomás", "Oliveira", "tomas@oliveira.tv", ROLE_REQUESTER, None),
    ("grace.lin", "Grace", "Lin", "grace@lumenlabs.io", ROLE_REQUESTER, None),
    ("marcus.webb", "Marcus", "Webb", "marcus@webbfitness.com", ROLE_REQUESTER, None),
    ("aisha.bello", "Aisha", "Bello", "aisha@bellostudio.africa", ROLE_REQUESTER, None),
]

MACROS = [
    (
        "Acknowledge and triage",
        "Thanks for flagging this — I've added it to the queue and I'm looking at it now. "
        "I'll come back with either a fix or a concrete next step within the SLA window.",
        Ticket.STATUS_PENDING,
        1,
    ),
    (
        "Ask for reproduction steps",
        "Could you send the exact steps you take before this happens, plus the browser and "
        "version you're on? A screenshot of the error text helps us reproduce it on the first try.",
        Ticket.STATUS_PENDING,
        2,
    ),
    (
        "Escalate to engineering",
        "I've escalated this to our engineering team with the details from this thread. "
        "They triage every escalation the same working day, and I'll post their findings here.",
        Ticket.STATUS_OPEN,
        3,
    ),
    (
        "Confirm fix and resolve",
        "This should be fixed now — we shipped the change and verified it on a test workspace. "
        "Please give it another try and reply here if anything still looks off; a reply reopens the ticket.",
        Ticket.STATUS_RESOLVED,
        4,
    ),
    (
        "Close as duplicate",
        "We're already tracking this in an existing ticket, so I'm closing this one to keep the "
        "thread in a single place. You'll get every update on the original ticket.",
        Ticket.STATUS_CLOSED,
        5,
    ),
]

# Each ticket: subject, description, requester, assignee, status, priority,
# opened (hours ago), SLA due (hours from now, negative = overdue),
# messages as (author, hours ago, body).
TICKETS = [
    {
        "subject": "Invoice export is missing March",
        "description": (
            "We exported January and February invoices without trouble, but the March CSV "
            "only contains the first eleven rows — the rest of the month is missing. The PDF "
            "export of the same month is complete. Could you check the export job?"
        ),
        "requester": "maya.chen",
        "assignee": "cenius",
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_HIGH,
        "opened": 6,
        "due_in": 2,
        "messages": [
            (
                "maya.chen",
                5.5,
                "Adding detail: the March CSV has 11 rows out of 74 invoices and the file is "
                "2 KB instead of the usual ~40 KB.",
            ),
            (
                "cenius",
                4.8,
                "Thanks Maya — reproduced on our staging workspace. The March batch stops after "
                "the first page. Re-running the export job now, I'll confirm when it lands.",
            ),
        ],
    },
    {
        "subject": "SSO login loop on Safari",
        "description": (
            "Since this morning Safari 17 bounces between /sso/start and the sign-in page. "
            "Chrome signs in normally on the same machine, so it looks browser specific."
        ),
        "requester": "priya.nair",
        "assignee": "dana.whitfield",
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_URGENT,
        "opened": 7,
        "due_in": 0.7,
        "messages": [
            ("priya.nair", 6.8, "Only Safari is affected. Clearing cookies did not help."),
            (
                "dana.whitfield",
                6.1,
                "Thanks Priya — testing with a clean Safari profile now. Early read: a SameSite "
                "cookie change we shipped yesterday. Will update within the hour.",
            ),
        ],
    },
    {
        "subject": "Card payment declined twice",
        "description": (
            "Both attempts on the Growth plan were declined today, and the bank says they never "
            "saw the authorisation. We are on a deadline for a client handover on Friday."
        ),
        "requester": "tomas.oliveira",
        "assignee": None,
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_URGENT,
        "opened": 9,
        "due_in": -1.2,
        "messages": [
            (
                "tomas.oliveira",
                8.6,
                "Tried a second card as well — same decline code. Happy to jump on a call if that helps.",
            ),
        ],
    },
    {
        "subject": "How do I rename a workspace?",
        "description": (
            "We set the workspace name to a placeholder during onboarding and now I can't find "
            "the rename option in settings. Where does it live?"
        ),
        "requester": "grace.lin",
        "assignee": "cenius",
        "status": Ticket.STATUS_PENDING,
        "priority": Ticket.PRIORITY_LOW,
        "opened": 26,
        "due_in": 9,
        "messages": [
            (
                "cenius",
                24,
                "Settings → Workspace → General has a “Workspace name” field. Renaming keeps all "
                "existing links. Tell me if the field is greyed out for your account.",
            ),
            ("grace.lin", 20, "Found it, thank you. Feel free to close this once you've confirmed."),
        ],
    },
    {
        "subject": "CSV import fails at row 4200",
        "description": (
            "Our contact import stops at row 4200 of a 12,000-row file and the error only says "
            "“import failed”. The file is UTF-8 and imports fine into a spreadsheet."
        ),
        "requester": "marcus.webb",
        "assignee": "dana.whitfield",
        "status": Ticket.STATUS_PENDING,
        "priority": Ticket.PRIORITY_HIGH,
        "opened": 30,
        "due_in": -3,
        "messages": [
            (
                "dana.whitfield",
                27,
                "Could you attach the row range 4195–4205 of the CSV (as text, not an attachment)? "
                "I suspect a stray delimiter in one line, which stops the parser silently.",
            ),
        ],
    },
    {
        "subject": "Feature request: dark mode",
        "description": (
            "Half the team works late and the light theme is rough on the eyes at 22:00. "
            "A dark theme that follows the OS setting would be a big win."
        ),
        "requester": "aisha.bello",
        "assignee": None,
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_LOW,
        "opened": 50,
        "due_in": 7,
        "messages": [],
    },
    {
        "subject": "Weekly digest email never arrives",
        "description": (
            "The Monday digest stopped arriving three weeks ago. Other transactional emails "
            "(invites, receipts) still come through to the same address."
        ),
        "requester": "priya.nair",
        "assignee": "omar.haddad",
        "status": Ticket.STATUS_RESOLVED,
        "priority": Ticket.PRIORITY_NORMAL,
        "opened": 74,
        "due_in": 5,
        "messages": [
            (
                "omar.haddad",
                70,
                "Found it — the digest was suppressed because a delivery once bounced. I've "
                "cleared the suppression and sent a test digest; it should land within the hour.",
            ),
            ("priya.nair", 68, "Received it. Thanks for the quick turnaround!"),
        ],
    },
    {
        "subject": "Can I export audit logs?",
        "description": (
            "Our compliance review needs the admin audit log for the last six months. "
            "Is there an export, or do we need to pull it from the API?"
        ),
        "requester": "grace.lin",
        "assignee": "cenius",
        "status": Ticket.STATUS_CLOSED,
        "priority": Ticket.PRIORITY_LOW,
        "opened": 120,
        "due_in": 3,
        "messages": [
            (
                "cenius",
                116,
                "Yes: Settings → Audit log → Export CSV covers up to 12 months and includes the "
                "actor, action and timestamp. I've attached nothing here, but the button is on that page.",
            ),
            ("grace.lin", 114, "Perfect, exported it. Closing this out."),
        ],
    },
    {
        "subject": "Billing: upgrading mid-cycle",
        "description": (
            "If we upgrade from Starter to Growth tomorrow, does the remaining Starter credit "
            "carry over, or do we pay the full Growth price for this month?"
        ),
        "requester": "maya.chen",
        "assignee": None,
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_NORMAL,
        "opened": 12,
        "due_in": 6,
        "messages": [],
    },
    {
        "subject": "Mobile app crashes on photo upload",
        "description": (
            "The iOS app closes itself when I attach a photo larger than about 8 MB. "
            "Reproducible on an iPhone 13 with the latest app update."
        ),
        "requester": "marcus.webb",
        "assignee": "omar.haddad",
        "status": Ticket.STATUS_OPEN,
        "priority": Ticket.PRIORITY_HIGH,
        "opened": 4,
        "due_in": 1.1,
        "messages": [
            (
                "marcus.webb",
                3.5,
                "It happens on Wi-Fi and on mobile data, so it doesn't look like a connection issue.",
            ),
            (
                "omar.haddad",
                2.9,
                "Thanks — we've got a crash report that matches. The upload buffer doesn't chunk "
                "large photos; engineering is on it. Please keep the ticket open until we ship.",
            ),
        ],
    },
    {
        "subject": "Add a second admin seat",
        "description": (
            "We need a second admin so our operations lead can manage billing while I'm on leave. "
            "How do we add one without sharing my login?"
        ),
        "requester": "aisha.bello",
        "assignee": "dana.whitfield",
        "status": Ticket.STATUS_RESOLVED,
        "priority": Ticket.PRIORITY_NORMAL,
        "opened": 96,
        "due_in": -6,
        "messages": [
            (
                "dana.whitfield",
                92,
                "Settings → Members → Invite, then switch their role to Admin. Each seat needs its "
                "own email address; we never allow shared logins.",
            ),
        ],
    },
    {
        "subject": "Webhook retries are duplicated",
        "description": (
            "When our endpoint times out, we receive the same webhook up to four times with "
            "different delivery ids. Should we be de-duplicating on the event id?"
        ),
        "requester": "tomas.oliveira",
        "assignee": "cenius",
        "status": Ticket.STATUS_PENDING,
        "priority": Ticket.PRIORITY_URGENT,
        "opened": 5,
        "due_in": -0.4,
        "messages": [
            (
                "cenius",
                4.2,
                "Yes — de-duplicate on the event id (not the delivery id), retries share it. "
                "We're also adding an exponential backoff after three failed deliveries.",
            ),
            (
                "tomas.oliveira",
                3.1,
                "Good to know. Can you confirm the retry window so we can size our cache TTL?",
            ),
        ],
    },
]


class Command(BaseCommand):
    help = "Create the demo agents, requesters, macros and sample tickets (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = int(options.get("verbosity", 1)) == 0
        now = timezone.now()
        people = {}
        created_people = 0

        for username, first, last, email, role, password in PEOPLE:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": first, "last_name": last},
            )
            if created:
                created_people += 1
                if password:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()
            else:
                changed = False
                for field, value in (("email", email), ("first_name", first), ("last_name", last)):
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        changed = True
                if password and not user.check_password(password):
                    user.set_password(password)
                    changed = True
                if changed:
                    user.save()
            Profile.objects.update_or_create(user=user, defaults={"role": role})
            people[username] = user

        macros_created = 0
        for name, body, set_status, position in MACROS:
            _, created = Macro.objects.update_or_create(
                name=name,
                defaults={"body": body, "set_status": set_status, "position": position},
            )
            macros_created += 1 if created else 0

        tickets_created = 0
        messages_created = 0
        for entry in TICKETS:
            requester = people[entry["requester"]]
            assignee = people[entry["assignee"]] if entry["assignee"] else None
            opened_at = now - timedelta(hours=entry["opened"])
            ticket, created = Ticket.objects.get_or_create(
                subject=entry["subject"],
                requester=requester,
                defaults={
                    "description": entry["description"],
                    "status": entry["status"],
                    "priority": entry["priority"],
                    "assignee": assignee,
                    "sla_due_at": now + timedelta(hours=entry["due_in"]),
                },
            )
            if created:
                tickets_created += 1

            if created:
                Ticket.objects.filter(pk=ticket.pk).update(
                    created_at=opened_at, updated_at=opened_at
                )
                ticket.created_at = opened_at
                ticket.updated_at = opened_at

            if not created:
                # Keep demo rows fresh on a rerun: the SLA clock should never be
                # stuck in the past just because the database was seeded weeks ago.
                ticket.assignee = assignee
                ticket.sla_due_at = now + timedelta(hours=entry["due_in"])
                ticket.save(update_fields=["assignee", "sla_due_at", "updated_at"])

            last_message_at = opened_at
            for author_username, hours_ago, body in entry["messages"]:
                author = people[author_username]
                message, message_created = Message.objects.get_or_create(
                    ticket=ticket, author=author, body=body
                )
                sent_at = now - timedelta(hours=hours_ago)
                if message_created:
                    messages_created += 1
                    Message.objects.filter(pk=message.pk).update(created_at=sent_at)
                last_message_at = max(last_message_at, sent_at)

            if entry["messages"]:
                Ticket.objects.filter(pk=ticket.pk).update(updated_at=last_message_at)

        if quiet:
            return

        self.stdout.write(self.style.SUCCESS("Deskline demo data is ready."))
        self.stdout.write(
            "  users:    %d total (%d created) — demo agent `cenius`, demo requester `maya.chen` "
            "(password documented in README and shown on the sign-in card)"
            % (User.objects.count(), created_people)
        )
        self.stdout.write(
            "  macros:   %d total (%d created)" % (Macro.objects.count(), macros_created)
        )
        self.stdout.write(
            "  tickets:  %d total (%d created)" % (Ticket.objects.count(), tickets_created)
        )
        self.stdout.write(
            "  messages: %d total (%d created)" % (Message.objects.count(), messages_created)
        )
