from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from attendance.models import ServiceType

ALL = ["add", "change", "delete", "view"]

# role -> {model: actions}; "app.model" for the door-terminal models (biometrics also has a Scan model)
ROLES = {
    # Pastor / church admin: everything in phase 1.
    "Church Admin": {
        "member": ALL, "household": ALL, "service": ALL, "servicetype": ALL, "attendance": ALL,
        "checkincard": ALL, "scan": ["add", "view"], "checkinsettings": ["change", "view"], "faceprofile": ALL,
        "biometrics.device": ALL, "biometrics.identity": ALL, "biometrics.consent": ALL, "biometrics.scan": ["view"],
        "biometrics.devicecommand": ["view"],
    },
    # Secretary: maintains member records and the service schedule, reads attendance.
    "Secretary": {
        "member": ["add", "change", "view"], "household": ["add", "change", "view"],
        "service": ["add", "change", "view"], "servicetype": ["view"], "attendance": ["view"],
        "checkincard": ["add", "change", "view"], "scan": ["view"], "faceprofile": ["add", "delete", "view"],
        "biometrics.consent": ["add", "change", "view"], "biometrics.identity": ["add", "view"],
        "biometrics.device": ["view"], "biometrics.scan": ["view"],
    },
    # Usher: takes attendance, can look members up and add first-time visitors at the door.
    "Usher": {
        "member": ["view"], "household": ["view"],
        "service": ["add", "change", "view"], "servicetype": ["view"], "attendance": ["add", "view"],
        "checkincard": ["view"], "scan": ["add", "view"],
        "biometrics.device": ["view"], "biometrics.scan": ["view"],
    },
    # A tablet or laptop left at the door running the self check-in kiosk, and nothing else.
    "Check-in Kiosk": {"scan": ["add"]},
}

DEFAULT_SERVICE_TYPES = [
    # name, weekday (Mon=0), start time
    ("Sunday Worship", 6, "09:30"),
    ("Sunday School", 6, "08:30"),
    ("Sunday Afternoon Service", 6, "14:00"),
    ("Prayer Meeting", 2, "19:00"),
    ("Youth Fellowship", 5, "15:00"),
]


class Command(BaseCommand):
    help = "Create the default staff roles (groups) and service types. Safe to run repeatedly."

    def handle(self, *args, **options):
        for role, apps in ROLES.items():  # noqa: B007
            group, _ = Group.objects.get_or_create(name=role)
            perms = []
            for model, actions in apps.items():
                app_labels = ["members", "attendance", "checkin"]
                if "." in model:
                    app_label, model = model.split(".")
                    app_labels = [app_label]
                perms += Permission.objects.filter(
                    content_type__app_label__in=app_labels,
                    codename__in=[f"{action}_{model}" for action in actions],
                )
            group.permissions.set(perms)
            self.stdout.write(f"Role {role}: {len(perms)} permissions")

        if not ServiceType.objects.exists():
            for order, (name, weekday, start) in enumerate(DEFAULT_SERVICE_TYPES):
                ServiceType.objects.create(name=name, weekday=weekday, start_time=start, order=order)
            self.stdout.write(f"Created {len(DEFAULT_SERVICE_TYPES)} service types")
