"""
Which check-in modes are on. Several can run side by side; QR is on by default.

  qr           QR stickers read by the kiosk camera (Android tablet)
  fingerprint  ZKTeco-class terminal at the door (biometrics app)
  face         face recognition, on the terminal and/or the kiosk camera

SELF_CHECKIN_ENABLED in the environment is a master switch: False turns every mode off.
Admins turn single modes on or off at Self check-in > Modes (CheckinSettings).
"""

from functools import wraps

from django.conf import settings
from django.http import Http404

QR, FINGERPRINT, FACE = "qr", "fingerprint", "face"
ALL_MODES = (QR, FINGERPRINT, FACE)


def modes(request=None):
    """The set of modes that are on. Cached on the request when one is given."""
    if request is not None and hasattr(request, "_checkin_modes"):
        return request._checkin_modes
    if not getattr(settings, "SELF_CHECKIN_ENABLED", False):
        result = frozenset()
    else:
        from .models import CheckinSettings

        s = CheckinSettings.load()
        result = frozenset(m for m, on in ((QR, s.qr_enabled), (FINGERPRINT, s.fingerprint_enabled), (FACE, s.face_enabled)) if on)
    if request is not None:
        request._checkin_modes = result
    return result


def mode_on(name, request=None):
    return name in modes(request)


def terminals_on(request=None):
    """Door terminals are used for fingerprint and for terminal face recognition."""
    return bool(modes(request) & {FINGERPRINT, FACE})


def requires_mode(*names):
    """404 the view unless at least one of the given modes is on (any mode, when none are given)."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            on = modes(request)
            if not (on & set(names) if names else on):
                raise Http404
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def requires_settings_access(view):
    """The Modes page itself stays reachable while every mode is off (but not when the master switch is off)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not getattr(settings, "SELF_CHECKIN_ENABLED", False):
            raise Http404
        return view(request, *args, **kwargs)
    return wrapper
