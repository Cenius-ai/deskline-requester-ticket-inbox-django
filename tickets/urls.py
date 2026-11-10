from django.urls import path

from . import views_agent, views_auth, views_portal, views_ticket

urlpatterns = [
    path("", views_agent.root, name="root"),
    path("health/", views_agent.health, name="health"),
    path("accounts/login/", views_auth.sign_in, name="sign_in"),
    path("login/", views_auth.sign_in, name="sign_in_alias"),
    path("accounts/signup/", views_auth.sign_up, name="sign_up"),
    path("accounts/logout/", views_auth.sign_out, name="sign_out"),
    path("inbox", views_agent.inbox, name="inbox"),
    path("inbox/", views_agent.inbox, name="inbox_slash"),
    path("portal", views_portal.portal, name="portal"),
    path("portal/", views_portal.portal, name="portal_slash"),
    path("portal/tickets/new", views_portal.portal_new, name="portal_new"),
    path("portal/tickets/new/", views_portal.portal_new, name="portal_new_slash"),
    path("tickets/<int:pk>", views_ticket.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/", views_ticket.ticket_detail, name="ticket_detail_slash"),
    path("tickets/<int:pk>/reply", views_ticket.ticket_reply, name="ticket_reply"),
    path("tickets/<int:pk>/update", views_ticket.ticket_update, name="ticket_update"),
    path("tickets/<int:pk>/delete", views_ticket.ticket_delete, name="ticket_delete"),
    path("tickets/<int:pk>/delete/", views_ticket.ticket_delete, name="ticket_delete_slash"),
    path("tickets/<int:pk>/macro", views_ticket.ticket_macro, name="ticket_macro"),
]
