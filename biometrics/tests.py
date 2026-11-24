from datetime import date, datetime, time

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from attendance.models import Attendance, Service
from core.tests import BaseTestCase

from .models import Consent, Device, DeviceCommand, Identity, Scan
from .services import ConsentRequired, find_service, record_consent, register_identity, withdraw_consent

SUNDAY = date(2026, 11, 22)


def at(hour, minute=0, day=SUNDAY):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def set_modes(qr=True, fingerprint=True, face=True):
    from checkin.models import CheckinSettings

    s = CheckinSettings.load()
    s.qr_enabled, s.fingerprint_enabled, s.face_enabled = qr, fingerprint, face
    s.save()


class BiometricTestCase(BaseTestCase):
    def setUp(self):
        set_modes()
        self.device = Device.objects.create(serial_number="SN1", is_active=True)

    def enroll(self, member):
        record_consent(member, self.admin)
        return register_identity(member)


class ConsentTests(BiometricTestCase):
    def test_registration_requires_consent(self):
        with self.assertRaises(ConsentRequired):
            register_identity(self.juan)

    def test_register_pushes_user_to_devices(self):
        identity = self.enroll(self.juan)
        self.assertEqual(identity.pin, "1")
        cmd = DeviceCommand.objects.get()
        self.assertIn("DATA UPDATE USERINFO PIN=1", cmd.command)

    def test_withdraw_deletes_identity_and_device_user(self):
        self.enroll(self.juan)
        withdraw_consent(self.juan)
        self.assertFalse(Identity.objects.exists())
        self.assertFalse(Consent.objects.get().is_active)
        self.assertIn("DATA DELETE USERINFO PIN=1", DeviceCommand.objects.last().command)


class ScanMatchingTests(BiometricTestCase):
    def test_auto_opens_and_picks_closest_service(self):
        # setup_roles seeds Sunday School 8:30 and Sunday Worship 9:30 on Sundays.
        self.assertEqual(find_service(at(9, 20)).service_type.name, "Sunday Worship")
        self.assertEqual(find_service(at(8, 25)).service_type.name, "Sunday School")
        self.assertTrue(Service.objects.filter(date=SUNDAY).count() >= 3)

    def test_outside_any_window(self):
        self.assertIsNone(find_service(at(9, 0, day=date(2026, 11, 24))))  # Tuesday: nothing scheduled

    def test_rescheduled_time_is_respected(self):
        afternoon = Service.objects.create(service_type=self.worship, date=date(2026, 11, 28), start_time=time(16, 0))
        self.assertEqual(find_service(at(15, 50, day=date(2026, 11, 28))), afternoon)


class AdmsProtocolTests(BiometricTestCase):
    def test_handshake_registers_unknown_device_inactive(self):
        resp = self.client.get("/iclock/cdata", {"SN": "NEW-123", "options": "all"})
        self.assertContains(resp, "GET OPTION FROM: NEW-123")
        self.assertFalse(Device.objects.get(serial_number="NEW-123").is_active)

    def test_attlog_push_checks_member_in(self):
        self.enroll(self.juan)
        body = "1\t2026-11-22 09:20:00\t0\t1\t0\t0\n99\t2026-11-22 09:21:00\t0\t1\t0\t0\n1\t2026-11-22 09:25:00\t0\t15\n"
        resp = self.client.post("/iclock/cdata?SN=SN1&table=ATTLOG&Stamp=1", body, content_type="text/plain")
        self.assertContains(resp, "OK: 3")
        att = Attendance.objects.get(member=self.juan)
        self.assertEqual(att.source, "fingerprint")
        self.assertEqual(att.checked_in_at, at(9, 20))  # scan time, not upload time
        self.assertEqual(att.service.service_type.name, "Sunday Worship")
        results = list(Scan.objects.order_by("scanned_at").values_list("result", flat=True))
        self.assertEqual(results, ["checked_in", "unknown_pin", "duplicate"])

    def test_face_scan_counts_as_face(self):
        self.enroll(self.juan)
        self.client.post("/iclock/cdata?SN=SN1&table=ATTLOG", "1\t2026-11-22 09:20:00\t0\t15", content_type="text/plain")
        self.assertEqual(Attendance.objects.get().source, "face")

    def test_scan_of_a_mode_that_is_off_is_not_counted(self):
        set_modes(fingerprint=True, face=False)
        self.enroll(self.juan)
        self.client.post("/iclock/cdata?SN=SN1&table=ATTLOG", "1\t2026-11-22 09:20:00\t0\t15", content_type="text/plain")
        self.assertFalse(Attendance.objects.exists())
        self.assertEqual(Scan.objects.get().result, "mode_off")

    def test_inactive_device_scans_are_ignored(self):
        self.enroll(self.juan)
        Device.objects.create(serial_number="ROGUE")
        self.client.post("/iclock/cdata?SN=ROGUE&table=ATTLOG", "1\t2026-11-22 09:20:00\t0\t1", content_type="text/plain")
        self.assertFalse(Attendance.objects.exists())
        self.assertEqual(Scan.objects.get().result, "device_inactive")

    def test_operlog_marks_enrollment_but_discards_template(self):
        self.enroll(self.juan)
        self.client.post("/iclock/cdata?SN=SN1&table=OPERLOG", "FP PIN=1\tFID=6\tSize=1024\tValid=1\tTMP=AAAA", content_type="text/plain")
        self.assertTrue(Identity.objects.get().has_fingerprint)

    def test_command_poll_and_ack(self):
        self.enroll(self.juan)
        cmd = DeviceCommand.objects.get()
        resp = self.client.get("/iclock/getrequest", {"SN": "SN1"})
        self.assertContains(resp, f"C:{cmd.pk}:DATA UPDATE USERINFO")
        self.assertEqual(self.client.get("/iclock/getrequest", {"SN": "SN1"}).content, b"OK")
        self.client.post("/iclock/devicecmd?SN=SN1", f"ID={cmd.pk}&Return=0&CMD=DATA", content_type="text/plain")
        cmd.refresh_from_db()
        self.assertEqual(cmd.status, "done")


class BiometricUiTests(BiometricTestCase):
    def test_member_card_flow(self):
        self.login()
        url = self.juan.get_absolute_url()
        self.assertContains(self.client.get(url), "Record signed consent")
        self.client.post(reverse("biometrics:consent", args=[self.juan.pk]), {"form_reference": "F-001"})
        self.assertContains(self.client.get(url), "Register on terminals")
        self.client.post(reverse("biometrics:register", args=[self.juan.pk]))
        self.assertContains(self.client.get(url), "Device user <strong>#1</strong>")

    def test_simulator_scan(self):
        identity = self.enroll(self.juan)
        self.login()
        self.client.get(reverse("biometrics:simulator"))
        resp = self.client.post(reverse("biometrics:simulator"),
                                {"identity": identity.pk, "action": "finger", "when": "2026-11-22T09:15"},
                                headers={"HX-Request": "true"})
        self.assertContains(resp, "Thank you, Juan Dela Cruz!")
        self.assertContains(self.client.get(reverse("biometrics:overview")), "Juan Dela Cruz")

    def test_usher_cannot_use_simulator_or_consent(self):
        self.login(self.usher)
        self.assertEqual(self.client.get(reverse("biometrics:overview")).status_code, 200)
        self.assertEqual(self.client.get(reverse("biometrics:simulator")).status_code, 403)

    def test_terminals_off_when_fingerprint_and_face_are_off(self):
        set_modes(fingerprint=False, face=False)
        self.login()
        self.assertEqual(self.client.get(reverse("biometrics:overview")).status_code, 404)
        self.assertEqual(self.client.get("/iclock/cdata", {"SN": "X"}).status_code, 404)
        page = self.client.get(self.juan.get_absolute_url()).content.decode()
        self.assertNotIn("Record signed consent", page)
        self.assertNotIn("Door terminals</a>", self.client.get(reverse("dashboard")).content.decode())

    @override_settings(SELF_CHECKIN_ENABLED=False)
    def test_master_switch_hides_terminals(self):
        self.login()
        self.assertEqual(self.client.get("/iclock/cdata", {"SN": "X"}).status_code, 404)
