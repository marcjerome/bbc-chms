from django import forms
from django.utils import timezone

from core.validators import validate_phone

from .models import Household, Member


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "title", "first_name", "middle_name", "last_name", "suffix", "nickname",
            "gender", "birth_date", "civil_status", "occupation", "photo",
            "phone", "email", "address", "emergency_contact_name", "emergency_contact_phone",
            "household", "household_role",
            "status", "church_role", "first_visit_date", "salvation_date", "is_baptized", "baptism_date",
            "membership_date", "notes",
        ]
        widgets = {
            "birth_date": DateInput(),
            "first_visit_date": DateInput(),
            "salvation_date": DateInput(),
            "baptism_date": DateInput(),
            "membership_date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    # Field groups used by the template to lay the form out in sections.
    sections = [
        ("Personal", ["title", "first_name", "middle_name", "last_name", "suffix", "nickname",
                      "gender", "birth_date", "civil_status", "occupation", "photo"]),
        ("Contact", ["phone", "email", "address", "emergency_contact_name", "emergency_contact_phone"]),
        ("Household", ["household", "household_role"]),
        ("Church life", ["status", "church_role", "first_visit_date", "salvation_date", "is_baptized",
                         "baptism_date", "membership_date", "notes"]),
    ]

    def grouped_fields(self):
        return [(title, [self[name] for name in names]) for title, names in self.sections]

    # Dates in a person's walk: none can be in the future or before they were born.
    CHURCH_DATES = ["first_visit_date", "salvation_date", "baptism_date", "membership_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("phone", "emergency_contact_phone"):
            self.fields[name].validators.append(validate_phone)

    def clean(self):
        cleaned = super().clean()
        today = timezone.localdate()
        birth = cleaned.get("birth_date")
        for name in ["birth_date", *self.CHURCH_DATES]:
            value = cleaned.get(name)
            if value and value > today:
                self.add_error(name, "This date is in the future.")
            elif value and birth and name != "birth_date" and value < birth:
                self.add_error(name, "This date is before their birthday.")
        if cleaned.get("baptism_date"):
            cleaned["is_baptized"] = True
        if cleaned.get("household_role") and not cleaned.get("household"):
            self.add_error("household_role", "Choose a household first.")
        return cleaned


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name", "address_line", "barangay", "city", "province", "phone", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].validators.append(validate_phone)


class QuickVisitorForm(forms.ModelForm):
    """Minimal form ushers use to add a first-time visitor during check-in."""

    class Meta:
        model = Member
        fields = ["first_name", "last_name", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].validators.append(validate_phone)
