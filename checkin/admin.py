from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CheckinCard, CheckinSettings, FaceProfile, Scan


@admin.register(CheckinCard)
class CheckinCardAdmin(ModelAdmin):
    list_display = ["member", "code", "issued_at", "printed_at"]
    search_fields = ["member__first_name", "member__last_name", "code"]
    readonly_fields = ["code"]


@admin.register(Scan)
class ScanAdmin(ModelAdmin):
    list_display = ["scanned_at", "code", "member", "result", "service", "station"]
    list_filter = ["result", "station"]


@admin.register(CheckinSettings)
class CheckinSettingsAdmin(ModelAdmin):
    list_display = ["__str__", "qr_enabled", "fingerprint_enabled", "face_enabled", "face_match_threshold"]

    def has_add_permission(self, request):
        return not CheckinSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FaceProfile)
class FaceProfileAdmin(ModelAdmin):
    """The numbers themselves are never shown: they are sensitive personal information (RA 10173)."""

    list_display = ["member", "enrolled_at", "enrolled_by"]
    search_fields = ["member__first_name", "member__last_name"]
    exclude = ["descriptors"]
    readonly_fields = ["member", "enrolled_at", "enrolled_by"]

    def has_add_permission(self, request):
        return False  # enroll from the member's profile, with the camera
