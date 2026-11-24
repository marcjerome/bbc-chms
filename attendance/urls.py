from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.service_list, name="service_list"),
    path("services/<int:pk>/", views.service_checkin, name="service_checkin"),
    path("services/<int:pk>/edit/", views.service_update, name="service_update"),
    path("service-types/", views.servicetype_list, name="servicetype_list"),
    path("service-types/new/", views.servicetype_create, name="servicetype_create"),
    path("service-types/<int:pk>/edit/", views.servicetype_update, name="servicetype_update"),
    path("services/<int:pk>/delete/", views.service_delete, name="service_delete"),
    path("services/<int:pk>/toggle/<int:member_id>/", views.toggle_attendance, name="toggle"),
    path("services/<int:pk>/live/", views.service_live, name="service_live"),
    path("services/<int:pk>/guests/", views.adjust_guests, name="adjust_guests"),
    path("services/<int:pk>/visitor/", views.add_visitor, name="add_visitor"),
]
