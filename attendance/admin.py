from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Attendance, Service, ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    list_display = ["name", "weekday", "start_time", "is_active", "order"]
    list_editable = ["order", "is_active"]


class AttendanceInline(TabularInline):
    model = Attendance
    fields = ["member", "checked_in_at", "recorded_by"]
    readonly_fields = ["checked_in_at", "recorded_by"]
    autocomplete_fields = ["member"]
    extra = 0


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ["__str__", "service_type", "date", "guest_headcount"]
    list_filter = ["service_type"]
    search_fields = ["title", "service_type__name"]
    date_hierarchy = "date"
    inlines = [AttendanceInline]


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ["member", "service", "checked_in_at", "recorded_by"]
    list_filter = ["service__service_type"]
    search_fields = ["member__first_name", "member__last_name"]
    autocomplete_fields = ["member", "service"]
