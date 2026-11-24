from django.conf import settings
from django.db import models
from django.urls import reverse

from members.models import Member


class ServiceType(models.Model):
    """A recurring gathering, e.g. Sunday Worship, Sunday School, Prayer Meeting."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    name = models.CharField(max_length=100, unique=True)
    weekday = models.IntegerField(choices=Weekday.choices, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    """One occurrence of a gathering on a given date. Attendance is taken against it."""

    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name="services")
    date = models.DateField()
    start_time = models.TimeField(
        null=True, blank=True, help_text="Leave blank to use the service type's usual time."
    )
    title = models.CharField(
        max_length=150, blank=True, help_text='Optional, e.g. "Church Anniversary"'
    )
    guest_headcount = models.PositiveIntegerField(
        default=0, help_text="Unnamed guests/children counted but not checked in by name."
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "service_type__order"]
        constraints = [
            models.UniqueConstraint(fields=["service_type", "date"], name="unique_service_per_day"),
        ]

    def __str__(self):
        label = self.title or self.service_type.name
        return f"{label} — {self.date:%b %d, %Y}"

    def get_absolute_url(self):
        return reverse("attendance:service_checkin", args=[self.pk])

    @property
    def time(self):
        return self.start_time or self.service_type.start_time

    @property
    def is_rescheduled(self):
        """True when this occurrence's day or time differs from the type's usual schedule."""
        st = self.service_type
        moved_time = self.start_time and st.start_time and self.start_time != st.start_time
        moved_day = st.weekday is not None and self.date.weekday() != st.weekday
        return bool(moved_time or moved_day)

    @property
    def present_count(self):
        return self.attendances.count()

    @property
    def total_count(self):
        return self.present_count + self.guest_headcount


class Attendance(models.Model):
    class Source(models.TextChoices):
        USHER = "usher", "Usher"
        QR = "qr", "QR self check-in"
        FINGERPRINT = "fingerprint", "Fingerprint"
        FACE = "face", "Face recognition"

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="attendances")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="attendances")
    checked_in_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.USHER)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-checked_in_at"]
        constraints = [
            models.UniqueConstraint(fields=["service", "member"], name="unique_attendance"),
        ]

    def __str__(self):
        return f"{self.member} @ {self.service}"
