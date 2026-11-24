from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

from biometrics import adms
from core.auth_views import ChurchLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", ChurchLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("members/", include("members.urls")),
    path("attendance/", include("attendance.urls")),
    path("checkin/", include("checkin.urls")),
    path("biometrics/", include("biometrics.urls")),
    # ZKTeco ADMS device endpoint (fingerprint/face terminals call these paths directly).
    path("iclock/cdata", adms.cdata),
    path("iclock/getrequest", adms.getrequest),
    path("iclock/devicecmd", adms.devicecmd),
    path("", include("core.urls")),
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
