from django import forms
from django.utils import timezone

from members.forms import DateInput

from .models import Service, ServiceType


class TimeInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%H:%M")
        super().__init__(**kwargs)


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["service_type", "date", "start_time", "title", "notes"]
        widgets = {"date": DateInput(), "start_time": TimeInput(), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        types = ServiceType.objects.all()
        if not self.instance.pk:
            types = types.filter(is_active=True)
        self.fields["service_type"].queryset = types
        if not self.is_bound and not self.instance.pk:
            today = timezone.localdate()
            self.initial.setdefault("date", today)
            todays = ServiceType.objects.filter(is_active=True, weekday=today.weekday()).first()
            if todays:
                self.initial.setdefault("service_type", todays.pk)

    def validate_unique(self):
        # Surface the (service_type, date) constraint as a friendly form error.
        try:
            self.instance.validate_constraints()
        except forms.ValidationError:
            self.add_error(None, "That service already exists for this date. Open it from the list below.")


class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ["name", "weekday", "start_time", "is_active", "order"]
        widgets = {"start_time": TimeInput()}
        labels = {"weekday": "Usual day", "start_time": "Usual time", "is_active": "Active",
                  "order": "Sort order"}
        help_texts = {"order": "Lowest first. The first active type is the main service on the dashboard."}
