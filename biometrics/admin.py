from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Consent, Device, DeviceCommand, Identity, Scan


@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = ["__str__", "serial_number", "is_active", "last_seen", "last_ip"]
    list_filter = ["is_active"]


@admin.register(Identity)
class IdentityAdmin(ModelAdmin):
    list_display = ["member", "pin", "has_fingerprint", "has_face", "enrolled_at"]
    search_fields = ["member__first_name", "member__last_name", "pin"]


@admin.register(Consent)
class ConsentAdmin(ModelAdmin):
    list_display = ["member", "consented_on", "form_reference", "withdrawn_on", "recorded_by"]


@admin.register(Scan)
class ScanAdmin(ModelAdmin):
    list_display = ["scanned_at", "pin", "member", "result", "service", "device"]
    list_filter = ["result", "device"]


@admin.register(DeviceCommand)
class DeviceCommandAdmin(ModelAdmin):
    list_display = ["device", "command", "status", "created_at", "sent_at", "return_code"]
    list_filter = ["status"]
