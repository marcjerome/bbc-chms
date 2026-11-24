"""
Phase 2: self check-in at the kiosk tablet. Each person gets a sticker with a QR code (stuck inside their Bible);
the kiosk camera reads it and checks them into the service happening at that time. The QR holds only a random code,
never a name or any personal details. When face recognition is on, the same camera can also recognise enrolled faces.
Fingerprint/face door terminals live in the biometrics app. Which modes are on: CheckinSettings (feature.modes()).
"""

import secrets

from django.conf import settings
from django.db import models

from members.models import Member

# No 0/O, 1/I/L, so a code printed under the QR can be typed by hand without mix-ups.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 8
QR_PREFIX = "FLOCK-"


def new_code():
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not CheckinCard.objects.filter(code=code).exists():
            return code


class CheckinCard(models.Model):
    """A person's QR sticker. Reissuing gives a new code, so a lost sticker stops working."""

    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="checkin_card")
    code = models.CharField(max_length=16, unique=True)
    issued_at = models.DateTimeField(auto_now=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["member__last_name", "member__first_name"]

    def __str__(self):
        return f"{self.member} ({self.qr_text})"

    @property
    def qr_text(self):
        """What the QR code contains, and what is printed under it, e.g. FLOCK-7KQ2M9XH."""
        return f"{QR_PREFIX}{self.code}"


class Scan(models.Model):
    """Every read at the kiosk (QR code or face), including reads that didn't check anyone in."""

    FACE_CODE = "FACE"  # the `code` of a face read

    class Result(models.TextChoices):
        CHECKED_IN = "checked_in", "Checked in"
        DUPLICATE = "duplicate", "Already checked in"
        UNKNOWN_CODE = "unknown_code", "Unknown code"
        UNKNOWN_FACE = "unknown_face", "Face not recognised"
        NO_SERVICE = "no_service", "No service at this time"

    code = models.CharField(max_length=64)
    scanned_at = models.DateTimeField()
    result = models.CharField(max_length=20, choices=Result.choices)
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    service = models.ForeignKey(
        "attendance.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    station = models.CharField(max_length=50, blank=True, help_text='Where the kiosk is, e.g. "Main door"')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"{self.code} @ {self.scanned_at:%Y-%m-%d %H:%M}"


class CheckinSettings(models.Model):
    """Which check-in modes are on (one row). Several modes can run side by side; QR is the default."""

    qr_enabled = models.BooleanField("QR stickers", default=True)
    fingerprint_enabled = models.BooleanField("Fingerprint (door terminal)", default=False)
    face_enabled = models.BooleanField("Face recognition", default=False)
    face_match_threshold = models.FloatField(
        default=0.45,
        help_text="How alike two faces must be (tablet kiosk). Lower is stricter. Measured: the same person scores "
                  "about 0.2-0.35, different people 0.5 or more, so 0.45 leaves a safe margin.",
    )

    class Season(models.TextChoices):
        AUTO = "auto", "Automatic: Christmas from Dec 1 to Jan 6"
        CHRISTMAS = "christmas", "Christmas now"
        OFF = "off", "No decorations"

    kiosk_season = models.CharField("Kiosk decorations", max_length=12, choices=Season.choices, default=Season.AUTO)

    class Meta:
        verbose_name = verbose_name_plural = "check-in settings"

    def __str__(self):
        return "Check-in settings"

    def season_on(self, today):
        """The decoration theme to show on the kiosk today: "christmas" or ""."""
        if self.kiosk_season == self.Season.CHRISTMAS:
            return "christmas"
        if self.kiosk_season == self.Season.AUTO and (today.month == 12 or (today.month == 1 and today.day <= 6)):
            return "christmas"
        return ""

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class FaceProfile(models.Model):
    """
    What the kiosk tablet needs to recognise a face: a few 128-number "descriptors" computed in the browser from
    enrollment pictures. No photo is ever stored. Needs the member's written consent (RA 10173); withdrawing
    consent deletes the profile.
    """

    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="face_profile")
    descriptors = models.JSONField(default=list, help_text="Up to 5 lists of 128 numbers; never a photo")
    enrolled_at = models.DateTimeField(auto_now=True)
    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self):
        return f"Face: {self.member}"
