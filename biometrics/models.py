"""
Phase 2, Fingerprint and Face modes: check-in through ZKTeco-class door terminals (ADMS "push" protocol) and
Data Privacy Act (RA 10173) consent. Fingerprint/face templates stay on the device; this app only
stores which member a device PIN belongs to and the scan events.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from members.models import Member


class Device(models.Model):
    serial_number = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100, blank=True, help_text='e.g. "Main door"')
    location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(
        default=False, help_text="New devices register themselves and stay inactive until approved."
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "serial_number"]

    def __str__(self):
        return self.name or self.serial_number

    @property
    def is_online(self):
        return bool(self.last_seen and timezone.now() - self.last_seen < timezone.timedelta(minutes=5))


class Consent(models.Model):
    """Written consent to collect biometric data (sensitive personal information under RA 10173)."""

    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="biometric_consent")
    consented_on = models.DateField(default=timezone.localdate)
    form_reference = models.CharField(
        max_length=100, blank=True, help_text="Signed form number or where the paper copy is filed"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    withdrawn_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Consent: {self.member}"

    @property
    def is_active(self):
        return self.withdrawn_on is None


class Identity(models.Model):
    """Links a member to their user number (PIN) on the terminals."""

    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="biometric")
    pin = models.CharField("Device user ID", max_length=20, unique=True)
    has_fingerprint = models.BooleanField(default=False)
    has_face = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "identities"

    def __str__(self):
        return f"{self.member} (PIN {self.pin})"

    @property
    def is_enrolled(self):
        return self.has_fingerprint or self.has_face

    @classmethod
    def next_pin(cls):
        pins = [int(p) for p in cls.objects.values_list("pin", flat=True) if p.isdigit()]
        return str(max(pins, default=0) + 1)


class Scan(models.Model):
    class Result(models.TextChoices):
        CHECKED_IN = "checked_in", "Checked in"
        DUPLICATE = "duplicate", "Already checked in"
        UNKNOWN_PIN = "unknown_pin", "Unknown person"
        NO_SERVICE = "no_service", "No service at this time"
        DEVICE_INACTIVE = "device_inactive", "Device not approved"
        MODE_OFF = "mode_off", "Check-in mode is off"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="scans")
    pin = models.CharField(max_length=20)
    scanned_at = models.DateTimeField()
    verify_mode = models.CharField(max_length=10, blank=True, help_text="1 = fingerprint, 15 = face")
    result = models.CharField(max_length=20, choices=Result.choices)
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    service = models.ForeignKey(
        "attendance.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"PIN {self.pin} @ {self.scanned_at:%Y-%m-%d %H:%M}"

    @property
    def method(self):
        return "Face" if self.verify_mode == "15" else "Fingerprint"


class DeviceCommand(models.Model):
    """Commands queued for a terminal; it collects them on its next poll (/iclock/getrequest)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="commands")
    command = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    return_code = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.device}: {self.command[:40]}"
