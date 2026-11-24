from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Household, Member


class MemberInline(TabularInline):
    model = Member
    fields = ["first_name", "last_name", "household_role", "status"]
    extra = 0
    show_change_link = True


@admin.register(Household)
class HouseholdAdmin(ModelAdmin):
    list_display = ["name", "barangay", "city", "phone"]
    search_fields = ["name", "members__last_name"]
    inlines = [MemberInline]


@admin.register(Member)
class MemberAdmin(ModelAdmin):
    list_display = ["sort_name", "status", "phone", "household", "is_baptized", "membership_date"]
    list_filter = ["status", "gender", "is_baptized", "civil_status"]
    search_fields = ["first_name", "last_name", "nickname", "phone", "email"]
    autocomplete_fields = ["household"]
    date_hierarchy = "created_at"
