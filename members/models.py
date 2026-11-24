from datetime import date

from django.db import models
from django.urls import reverse


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Household(TimeStampedModel):
    """A family or household unit; members share the address."""

    name = models.CharField(max_length=150, help_text='e.g. "Dela Cruz Family"')
    address_line = models.CharField("Street / Purok", max_length=255, blank=True)
    barangay = models.CharField(max_length=100, blank=True, default="Barani")
    city = models.CharField("City / Municipality", max_length=100, blank=True, default="Batac City")
    province = models.CharField(max_length=100, blank=True, default="Ilocos Norte")
    phone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("members:household_detail", args=[self.pk])

    @property
    def full_address(self):
        parts = [self.address_line, f"Brgy. {self.barangay}" if self.barangay else "", self.city, self.province]
        return ", ".join(p for p in parts if p)


class Member(TimeStampedModel):
    class Status(models.TextChoices):
        VISITOR = "visitor", "Visitor"
        ATTENDEE = "attendee", "Regular attendee"
        MEMBER = "member", "Member"
        INACTIVE = "inactive", "Inactive"
        TRANSFERRED = "transferred", "Transferred"
        DECEASED = "deceased", "Deceased"

    # Statuses that count as part of the active congregation.
    ACTIVE_STATUSES = (Status.VISITOR, Status.ATTENDEE, Status.MEMBER)

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class CivilStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        WIDOWED = "widowed", "Widowed"
        SEPARATED = "separated", "Separated"

    class HouseholdRole(models.TextChoices):
        HEAD = "head", "Head"
        SPOUSE = "spouse", "Spouse"
        CHILD = "child", "Child"
        RELATIVE = "relative", "Relative"
        OTHER = "other", "Other"

    class Title(models.TextChoices):
        BRO = "Bro.", "Bro."
        SIS = "Sis.", "Sis."
        PASTOR = "Pastor", "Pastor"
        DEACON = "Deacon", "Deacon"

    # Personal
    title = models.CharField(max_length=20, choices=Title.choices, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=20, blank=True, help_text="Jr., Sr., III")
    nickname = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    civil_status = models.CharField(max_length=20, choices=CivilStatus.choices, blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    photo = models.ImageField(upload_to="members/photos/", blank=True)

    # Contact
    phone = models.CharField("Mobile number", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(
        max_length=255, blank=True, help_text="Leave blank to use the household address."
    )
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)

    # Household
    household = models.ForeignKey(
        Household, null=True, blank=True, on_delete=models.SET_NULL, related_name="members"
    )
    household_role = models.CharField(max_length=20, choices=HouseholdRole.choices, blank=True)

    # Church life
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VISITOR)
    church_role = models.CharField(
        max_length=100, blank=True, help_text='Shown as a tag, e.g. "Head Usher", "Youth Leader"'
    )
    first_visit_date = models.DateField(null=True, blank=True)
    salvation_date = models.DateField(null=True, blank=True)
    is_baptized = models.BooleanField("Baptized", default=False)
    baptism_date = models.DateField(null=True, blank=True)
    membership_date = models.DateField("Date received as member", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("members:member_detail", args=[self.pk])

    @property
    def full_name(self):
        middle_initial = f"{self.middle_name[0]}." if self.middle_name else ""
        parts = [self.first_name, middle_initial, self.last_name, self.suffix]
        return " ".join(p for p in parts if p)

    @property
    def display_name(self):
        """Name with title, e.g. "Bro. Juan Dela Cruz"."""
        return " ".join(p for p in [self.title, self.first_name, self.last_name, self.suffix] if p)

    @property
    def sort_name(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        before_birthday = (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        return today.year - self.birth_date.year - before_birthday

    @property
    def display_address(self):
        if self.address:
            return self.address
        return self.household.full_address if self.household else ""

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES
