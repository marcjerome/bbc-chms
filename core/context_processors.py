from django.conf import settings

from checkin.feature import FACE, FINGERPRINT, QR, modes


def church(request):
    on = modes(request)
    return {
        "CHURCH_NAME": settings.CHURCH_NAME,
        "CHURCH_SHORT_NAME": settings.CHURCH_SHORT_NAME,
        "APP_NAME": settings.APP_NAME,
        # Self check-in modes (Self check-in > Modes). SELF_CHECKIN_ENABLED: at least one mode is on.
        "CHECKIN_AVAILABLE": settings.SELF_CHECKIN_ENABLED,  # master switch: the Modes page is reachable
        "CHECKIN_MODES": on,
        "SELF_CHECKIN_ENABLED": bool(on),
        "QR_ON": QR in on,
        "FINGERPRINT_ON": FINGERPRINT in on,
        "FACE_ON": FACE in on,
        "TERMINALS_ON": bool(on & {FINGERPRINT, FACE}),
        "KIOSK_ON": bool(on & {QR, FACE}),
    }
