"""Door terminal (fingerprint / face) logic, shared by the ADMS device endpoint and the in-app simulator."""

from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from attendance.models import Attendance
from checkin.feature import FACE, FINGERPRINT, modes
from checkin.services import find_service  # same service-matching rules as the QR kiosk

from .models import Consent, DeviceCommand, Identity, Scan

VERIFY_FINGERPRINT = "1"
VERIFY_FACE = "15"


class ConsentRequired(Exception):
    pass


# --- Scans ------------------------------------------------------------------------------------

@transaction.atomic
def record_scan(device, pin, when, verify_mode=VERIFY_FINGERPRINT):
    """Store one scan and turn it into attendance when possible. Returns the Scan."""
    scan = Scan(device=device, pin=pin, scanned_at=when, verify_mode=verify_mode)
    if not device.is_active:
        scan.result = Scan.Result.DEVICE_INACTIVE
        scan.save()
        return scan
    identity = Identity.objects.select_related("member").filter(pin=pin).first()
    if not identity:
        scan.result = Scan.Result.UNKNOWN_PIN
        scan.save()
        return scan
    scan.member = identity.member
    mode = FACE if verify_mode == VERIFY_FACE else FINGERPRINT
    if mode not in modes():  # e.g. a face scan while only Fingerprint mode is on
        scan.result = Scan.Result.MODE_OFF
        scan.save()
        return scan
    scan.service = find_service(when)
    if not scan.service:
        scan.result = Scan.Result.NO_SERVICE
    else:
        try:
            with transaction.atomic():
                att = Attendance.objects.create(
                    service=scan.service, member=identity.member, source=Attendance.Source.FACE if mode == FACE else Attendance.Source.FINGERPRINT
                )
                # Record when the person actually scanned (terminals may upload late), not upload time.
                Attendance.objects.filter(pk=att.pk).update(checked_in_at=when)
            scan.result = Scan.Result.CHECKED_IN
        except IntegrityError:
            scan.result = Scan.Result.DUPLICATE
    scan.save()
    return scan


def parse_device_time(value):
    """ADMS timestamps are device-local, e.g. '2026-11-22 09:12:45'."""
    naive = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive)


def ingest_attlog(device, body):
    """Parse an ATTLOG push: one scan per line, tab-separated PIN, time, status, verify, ..."""
    scans = []
    for line in body.splitlines():
        fields = line.split("\t")
        if len(fields) < 2 or not fields[0].strip():
            continue
        try:
            when = parse_device_time(fields[1])
        except ValueError:
            continue
        verify = fields[3].strip() if len(fields) > 3 else VERIFY_FINGERPRINT
        scans.append(record_scan(device, fields[0].strip(), when, verify))
    return scans


def ingest_operlog(device, body):
    """
    Enrollment notices pushed by the device after a finger/face is registered at the terminal.
    Templates (TMP=...) are deliberately ignored: biometric data is not stored on the server.
    """
    count = 0
    for line in body.splitlines():
        head, _, rest = line.partition(" ")
        params = dict(p.split("=", 1) for p in rest.split("\t") if "=" in p)
        pin = params.get("PIN")
        if not pin:
            continue
        identity = Identity.objects.filter(pin=pin).first()
        if not identity:
            continue
        if head in ("FP", "FINGERTMP") or (head == "BIODATA" and params.get("Type") == "1"):
            identity.has_fingerprint = True
        elif head in ("FACE", "BIOPHOTO") or (head == "BIODATA" and params.get("Type") == "9"):
            identity.has_face = True
        else:
            continue
        identity.enrolled_at = identity.enrolled_at or timezone.now()
        identity.save()
        count += 1
    return count


# --- Consent & enrollment ---------------------------------------------------------------------

def record_consent(member, user, form_reference="", on=None):
    consent, _ = Consent.objects.update_or_create(
        member=member,
        defaults={"consented_on": on or timezone.localdate(), "form_reference": form_reference,
                  "recorded_by": user, "withdrawn_on": None},
    )
    return consent


def queue_for_all_devices(command):
    from .models import Device

    for device in Device.objects.filter(is_active=True):
        DeviceCommand.objects.create(device=device, command=command)


def register_identity(member):
    """Give the member a device user ID and push it to every active terminal. Needs consent."""
    consent = getattr(member, "biometric_consent", None)
    if not consent or not consent.is_active:
        raise ConsentRequired("Record the member's signed consent first (RA 10173).")
    identity, created = Identity.objects.get_or_create(member=member, defaults={"pin": Identity.next_pin()})
    name = member.display_name[:24].replace("\t", " ")
    queue_for_all_devices(f"DATA UPDATE USERINFO PIN={identity.pin}\tName={name}\tPri=0")
    return identity


def withdraw_consent(member):
    """Consent withdrawn: delete the member from every terminal, forget their PIN and their kiosk face profile."""
    from checkin.models import FaceProfile

    FaceProfile.objects.filter(member=member).delete()
    consent = getattr(member, "biometric_consent", None)
    if consent:
        consent.withdrawn_on = timezone.localdate()
        consent.save()
    identity = getattr(member, "biometric", None)
    if identity:
        queue_for_all_devices(f"DATA DELETE USERINFO PIN={identity.pin}")
        identity.delete()
