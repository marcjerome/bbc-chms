"""Kiosk self check-in logic: turning a QR code or a recognised face into attendance for the right service."""

import math
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType

from .models import QR_PREFIX, CheckinCard, CheckinSettings, FaceProfile, Scan, new_code


def _start(service):
    t = service.time
    return timezone.make_aware(datetime.combine(service.date, t)) if t else None


def find_service(when):
    """
    The service a scan at `when` belongs to: among that day's services, the one whose window
    (start - BEFORE .. start + AFTER) contains the scan, closest start first. If no service exists
    yet for that day, services are opened automatically from the active service types scheduled
    on that weekday, so nobody has to "open" the service before the doors open. Each regular service
    opens on its own, even when a special event was added for that day. One that was moved to another
    day within a week (same type, no title of its own) is not opened again on its usual day; an extra
    occurrence with a title (e.g. "Christmas Eve" using the Sunday Worship type) does not count as a move.
    """
    local = timezone.localtime(when)
    day = local.date()
    for st in ServiceType.objects.filter(is_active=True, weekday=day.weekday()):
        week = (day - timedelta(days=6), day + timedelta(days=6))
        moved = Service.objects.filter(service_type=st, date__range=week, title="").exclude(date__week_day=(day.isoweekday() % 7) + 1)
        if not moved.exists():
            Service.objects.get_or_create(service_type=st, date=day)

    before = timedelta(minutes=settings.CHECKIN_WINDOW_BEFORE)
    after = timedelta(minutes=settings.CHECKIN_WINDOW_AFTER)
    candidates = []
    for service in Service.objects.filter(date=day).select_related("service_type"):
        start = _start(service)
        if start is None:
            candidates.append((timedelta.max, service))  # untimed service: last resort
        elif start - before <= when <= start + after:
            candidates.append((abs(when - start), service))
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1] if candidates else None


def normalize_code(raw):
    """Accept the QR text ("FLOCK-7KQ2M9XH") or the code typed by hand, any case, with stray spaces."""
    text = "".join(raw.split()).upper()
    if text.startswith(QR_PREFIX):
        text = text[len(QR_PREFIX):]
    return text.replace("-", "")


def _check_in(scan, member, when, user, source):
    """Turn a recognised read into attendance for the service happening at `when`."""
    scan.member = member
    scan.service = find_service(when)
    if not scan.service:
        scan.result = Scan.Result.NO_SERVICE
    else:
        try:
            with transaction.atomic():
                att = Attendance.objects.create(service=scan.service, member=member, source=source, recorded_by=user)
                Attendance.objects.filter(pk=att.pk).update(checked_in_at=when)
            scan.result = Scan.Result.CHECKED_IN
        except IntegrityError:
            scan.result = Scan.Result.DUPLICATE
    scan.save()
    return scan


@transaction.atomic
def record_scan(raw_code, when=None, user=None, station=""):
    """Store one kiosk QR read and turn it into attendance when possible. Returns the Scan."""
    when = when or timezone.now()
    scan = Scan(code=raw_code.strip()[:64], scanned_at=when, station=station[:50], recorded_by=user)
    card = CheckinCard.objects.select_related("member").filter(code=normalize_code(raw_code)).first()
    if not card:
        scan.result = Scan.Result.UNKNOWN_CODE
        scan.save()
        return scan
    return _check_in(scan, card.member, when, user, Attendance.Source.QR)


# --- Face recognition at the kiosk ------------------------------------------------------------------
# The browser (face-api, offline) turns a face into a descriptor: 128 numbers. Two pictures of the same person
# give descriptors close together (Euclidean distance under ~0.5); different people are usually 0.6 or more apart.

DESCRIPTOR_LENGTH = 128
MAX_DESCRIPTORS = 5


def clean_descriptor(value):
    """A list of 128 finite numbers, or None."""
    try:
        d = [float(x) for x in value]
    except (TypeError, ValueError):
        return None
    if len(d) != DESCRIPTOR_LENGTH or not all(math.isfinite(x) and abs(x) < 10 for x in d):
        return None
    return d


def best_face_match(descriptor, threshold=None):
    """(member, distance) of the closest enrolled face under the threshold, or (None, distance-or-None)."""
    threshold = CheckinSettings.load().face_match_threshold if threshold is None else threshold
    best, best_d = None, None
    for profile in FaceProfile.objects.select_related("member"):
        for known in profile.descriptors:
            d = math.dist(descriptor, known)
            if best_d is None or d < best_d:
                best, best_d = profile.member, d
    if best is not None and best_d < threshold:
        return best, best_d
    return None, best_d


@transaction.atomic
def record_face_scan(descriptor, when=None, user=None, station=""):
    """Store one kiosk face read and check the person in when the face is recognised. Returns the Scan."""
    when = when or timezone.now()
    scan = Scan(code=Scan.FACE_CODE, scanned_at=when, station=station[:50], recorded_by=user)
    member, _ = best_face_match(descriptor)
    if member is None:
        scan.result = Scan.Result.UNKNOWN_FACE
        scan.save()
        return scan
    return _check_in(scan, member, when, user, Attendance.Source.FACE)


class ConsentRequired(Exception):
    pass


def has_consent(member):
    consent = getattr(member, "biometric_consent", None)
    return bool(consent and consent.is_active)


def enroll_face(member, descriptors, user=None):
    """Save the member's face descriptors (no photos). Needs their signed consent (RA 10173)."""
    if not has_consent(member):
        raise ConsentRequired("Record the member's signed consent first (RA 10173).")
    clean = [d for d in (clean_descriptor(x) for x in descriptors) if d][:MAX_DESCRIPTORS]
    if len(clean) < 3:
        raise ValueError("Need at least 3 good pictures of the face.")
    profile, _ = FaceProfile.objects.update_or_create(member=member, defaults={"descriptors": clean, "enrolled_by": user})
    return profile


def issue_card(member, user=None):
    """Give the member a QR code, or a new one (the old sticker stops working)."""
    card = getattr(member, "checkin_card", None)
    if card is None:
        return CheckinCard.objects.create(member=member, code=new_code(), issued_by=user)
    card.code = new_code()
    card.issued_by = user
    card.printed_at = None
    card.save()
    return card


NAVY, BROWN, CREAM = "#041632", "#6B4310", "#F2EEE6"
# The Flock sheep (static/img/flock-logo.svg), drawn in a 100 x 100 box.
SHEEP = (
    '<rect width="100" height="100" rx="22" fill="#041632"/><g fill="#F2EEE6"><circle cx="31" cy="46" r="12"/>'
    '<circle cx="41" cy="34" r="12"/><circle cx="56" cy="32" r="12"/><circle cx="69" cy="41" r="12"/>'
    '<circle cx="72" cy="56" r="11"/><circle cx="62" cy="67" r="12"/><circle cx="46" cy="69" r="12"/>'
    '<circle cx="32" cy="60" r="11"/><circle cx="51" cy="51" r="19"/></g><g fill="#6B4310">'
    '<rect x="41" y="74" width="6" height="13" rx="3"/><rect x="54" y="74" width="6" height="13" rx="3"/>'
    '<ellipse cx="37" cy="51" rx="7" ry="3.5" transform="rotate(-20 37 51)"/>'
    '<ellipse cx="65" cy="51" rx="7" ry="3.5" transform="rotate(20 65 51)"/>'
    '<ellipse cx="51" cy="57" rx="11" ry="14"/></g><g fill="#F2EEE6"><circle cx="46.5" cy="55" r="1.9"/>'
    '<circle cx="55.5" cy="55" r="1.9"/></g>'
)
QUIET = 4        # modules of white around the code (the QR standard's quiet zone)
LOGO = 7         # the sheep covers 7 x 7 modules in the middle: about 8% of a version-2 code
BAND = 6         # height of the "BBC BARANI" band under the code, in modules


def qr_svg(text, scale=4, standalone=False, label=None):
    """
    The church's branded QR code as SVG: navy softly rounded squares, rounded corner eyes with brown centres,
    the Flock sheep in the middle and a navy band with the church name underneath. Rendered locally
    (no outside service). Inline SVG for a page, or `standalone` (with the SVG namespace) for an image.

    It stays easy to scan: the highest error correction (H, up to 30% damage) while the sheep covers
    only ~8%, the corner eyes and timing lines are untouched, and it is dark-on-white with a full
    quiet zone. Checked by checkin/tests.py and the e2e "QR design" tests.
    """
    from django.conf import settings
    from django.utils.html import escape

    import segno

    label = settings.CHURCH_SHORT_NAME.upper() if label is None else label
    # make_qr, not make: segno would pick Micro QR for short codes, which most cameras can't read.
    qr = segno.make_qr(text, error="h")
    matrix = [list(row) for row in qr.matrix]
    n = len(matrix)
    size = n + 2 * QUIET
    height = size + BAND
    lo = (n - LOGO) // 2
    hi = lo + LOGO

    def in_eye(r, c):
        return (r < 7 and c < 7) or (r < 7 and c >= n - 7) or (r >= n - 7 and c < 7)

    parts = []
    for r, row in enumerate(matrix):
        for c, dark in enumerate(row):
            if dark and not in_eye(r, c) and not (lo <= r < hi and lo <= c < hi):
                # Softly rounded squares, full size: separate round dots scan noticeably worse up close.
                parts.append(f'<rect x="{c + QUIET}" y="{r + QUIET}" width="1.02" height="1.02" rx="0.3"/>')
    dots = f'<g fill="{NAVY}">{"".join(parts)}</g>'

    eyes = []
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        x, y = c0 + QUIET, r0 + QUIET
        eyes.append(
            f'<path fill="{NAVY}" fill-rule="evenodd" d="M{x + 2},{y} h3 a2,2 0 0 1 2,2 v3 a2,2 0 0 1 -2,2 h-3 '
            f'a2,2 0 0 1 -2,-2 v-3 a2,2 0 0 1 2,-2z M{x + 2},{y + 1} a1,1 0 0 0 -1,1 v3 a1,1 0 0 0 1,1 h3 '
            f'a1,1 0 0 0 1,-1 v-3 a1,1 0 0 0 -1,-1z"/>'
            f'<rect x="{x + 2}" y="{y + 2}" width="3" height="3" rx="0.8" fill="{BROWN}"/>'
        )

    lx = ly = QUIET + lo
    logo = (f'<rect x="{lx - 0.4}" y="{ly - 0.4}" width="{LOGO + 0.8}" height="{LOGO + 0.8}" rx="1.6" fill="#fff"/>'
            f'<svg x="{lx + 0.3}" y="{ly + 0.3}" width="{LOGO - 0.6}" height="{LOGO - 0.6}" viewBox="0 0 100 100">'
            f'{SHEEP}</svg>')
    band = ""
    if label:
        band = (f'<path fill="{NAVY}" d="M0,{size} H{size} V{height - 2} a2,2 0 0 1 -2,2 H2 a2,2 0 0 1 -2,-2z"/>'
                f'<text x="{size / 2}" y="{size + BAND / 2 + 1.1}" text-anchor="middle" fill="{CREAM}" '
                f'font-family="Playfair Display, Georgia, serif" font-weight="700" font-size="3.1" '
                f'letter-spacing="0.35">{escape(label)}</text>')
    else:
        height = size
    ns = ' xmlns="http://www.w3.org/2000/svg"' if standalone else ""
    return (f'<svg{ns} viewBox="0 0 {size} {height}" width="{size * scale}" height="{height * scale}" '
            f'role="img" aria-label="QR code {escape(text)}">'
            f'<rect width="{size}" height="{height}" rx="2" fill="#fff"/>{dots}{"".join(eyes)}{logo}{band}</svg>')
