from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("", views.member_list, name="member_list"),
    path("birthdays/", views.birthdays, name="birthdays"),
    path("visitation/", views.followups, name="followups"),
    path("export.csv", views.member_export, name="member_export"),
    path("new/", views.member_create, name="member_create"),
    path("<int:pk>/", views.member_detail, name="member_detail"),
    path("<int:pk>/edit/", views.member_update, name="member_update"),
    path("<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("households/", views.household_list, name="household_list"),
    path("households/new/", views.household_create, name="household_create"),
    path("households/<int:pk>/", views.household_detail, name="household_detail"),
    path("households/<int:pk>/edit/", views.household_update, name="household_update"),
]
