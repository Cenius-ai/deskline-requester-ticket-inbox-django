from django.contrib import admin

from .models import Macro, Message, Profile, Ticket


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "status", "priority", "requester", "assignee", "sla_due_at")
    list_filter = ("status", "priority")
    search_fields = ("subject", "description", "requester__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("body",)


@admin.register(Macro)
class MacroAdmin(admin.ModelAdmin):
    list_display = ("name", "set_status", "position")
    list_editable = ("set_status", "position")
