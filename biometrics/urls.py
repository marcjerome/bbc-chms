from django.urls import path

from . import views

app_name = "biometrics"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("simulator/", views.simulator, name="simulator"),
    path("devices/<int:pk>/", views.device_update, name="device_update"),
    path("members/<int:member_id>/consent/", views.consent, name="consent"),
    path("members/<int:member_id>/register/", views.register, name="register"),
    path("members/<int:member_id>/withdraw/", views.withdraw, name="withdraw"),
]
