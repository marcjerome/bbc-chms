from django.urls import path

from . import views

app_name = "checkin"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("kiosk/", views.kiosk, name="kiosk"),
    path("kiosk/scan/", views.kiosk_scan, name="scan"),
    path("kiosk/face/", views.face_scan, name="face_scan"),
    path("modes/", views.modes_view, name="modes"),
    path("members/<int:member_id>/face/", views.face_enroll, name="face_enroll"),
    path("members/<int:member_id>/face/remove/", views.face_remove, name="face_remove"),
    path("stickers/", views.stickers, name="stickers"),
    path("stickers/issue/", views.issue_many, name="issue_many"),
    path("stickers/printed/", views.mark_printed, name="mark_printed"),
    path("members/<int:member_id>/issue/", views.issue, name="issue"),
    path("members/<int:member_id>/revoke/", views.revoke, name="revoke"),
    path("members/<int:member_id>/qr.svg", views.qr_image, name="qr"),
]
