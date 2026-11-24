import json
from datetime import datetime

from django import forms
from django.contrib import messages
from core.permissions import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from members.models import Household, Member

from .feature import FACE, QR, modes, requires_mode, requires_settings_access
from .models import CheckinCard, CheckinSettings, FaceProfile, Scan
from .services import (ConsentRequired, clean_descriptor, enroll_face, has_consent, issue_card, qr_svg,
                       record_face_scan, record_scan)


def _stats():
    active = Member.objects.filter(status__in=Member.ACTIVE_STATUSES)
    today = timezone.localdate()
    return {
        "active_people": active.count(),
        "with_card": CheckinCard.objects.filter(member__in=active).count(),
        "printed": CheckinCard.objects.filter(member__in=active, printed_at__isnull=False).count(),
        "today": Scan.objects.filter(scanned_at__date=today, result=Scan.Result.CHECKED_IN).count(),
    }


@requires_settings_access
@permission_required("checkin.view_scan")
def overview(request):
    context = {"scans": Scan.objects.select_related("member", "service__service_type")[:25], **_stats(),
               "faces": FaceProfile.objects.count()}
    template = "checkin/overview.html#scan_feed" if request.htmx else "checkin/overview.html"
    return render(request, template, context)


# --- Kiosk: the camera at the door ----------------------------------------------------------------

def _demo_time_allowed(user):
    return user.has_perm("checkin.change_checkincard")


def _kiosk_modes(request):
    """Modes this kiosk uses: the ones that are on, optionally narrowed per station with ?modes=qr or ?modes=face."""
    on = modes(request) & {QR, FACE}
    asked = {m for m in request.GET.get("modes", "").split(",") if m}
    return (on & asked) or on if asked else on


def _season():
    return CheckinSettings.load().season_on(timezone.localdate())


@requires_mode(QR, FACE)
@permission_required("checkin.add_scan")
def kiosk(request):
    kiosk_modes = _kiosk_modes(request)
    return render(request, "checkin/kiosk.html", {
        "station": request.GET.get("station", "Main door")[:50],
        "demo_time": _demo_time_allowed(request.user),
        "kiosk_qr": QR in kiosk_modes,
        "kiosk_face": FACE in kiosk_modes,
        "season": _season(),
    })


def _scan_time(request):
    if request.POST.get("when") and _demo_time_allowed(request.user):
        try:
            return timezone.make_aware(datetime.fromisoformat(request.POST["when"]))
        except ValueError:
            pass
    return None


@requires_mode(QR)
@permission_required("checkin.add_scan")
@require_POST
def kiosk_scan(request):
    code = request.POST.get("code", "")
    if not code.strip():
        return HttpResponse(status=400)
    scan = record_scan(code, when=_scan_time(request), user=request.user, station=request.POST.get("station", ""))
    return render(request, "checkin/kiosk.html#result", {"scan": scan, "season": _season()})


@requires_mode(FACE)
@permission_required("checkin.add_scan")
@require_POST
def face_scan(request):
    try:
        descriptor = clean_descriptor(json.loads(request.POST.get("descriptor", "")))
    except ValueError:
        descriptor = None
    if descriptor is None:
        return HttpResponse(status=400)
    scan = record_face_scan(descriptor, when=_scan_time(request), user=request.user, station=request.POST.get("station", ""))
    return render(request, "checkin/kiosk.html#result", {"scan": scan, "season": _season()})


# --- Modes: which ways of checking in are on ------------------------------------------------------

class ModesForm(forms.ModelForm):
    class Meta:
        model = CheckinSettings
        fields = ["qr_enabled", "fingerprint_enabled", "face_enabled", "face_match_threshold", "kiosk_season"]
        widgets = {"face_match_threshold": forms.NumberInput(attrs={"step": "0.01", "min": "0.3", "max": "0.7"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kiosk_season"].required = False  # left out: automatic

    def clean_kiosk_season(self):
        return self.cleaned_data.get("kiosk_season") or CheckinSettings.Season.AUTO

    def clean_face_match_threshold(self):
        value = self.cleaned_data["face_match_threshold"]
        if not 0.3 <= value <= 0.7:
            raise forms.ValidationError("Use a number from 0.30 (strict) to 0.70 (loose). 0.45 suits most churches.")
        return value


@requires_settings_access
@permission_required("checkin.change_checkinsettings")
def modes_view(request):
    form = ModesForm(request.POST or None, instance=CheckinSettings.load())
    if request.method == "POST" and form.is_valid():
        form.save()
        on = [label for field, label in (("qr_enabled", "QR"), ("fingerprint_enabled", "Fingerprint"), ("face_enabled", "Face"))
              if form.cleaned_data[field]]
        messages.success(request, f"Check-in modes saved: {', '.join(on) if on else 'all off'}.")
        return redirect("checkin:modes")
    return render(request, "checkin/modes.html", {"form": form})


# --- Face enrollment (kiosk tablet face recognition) ----------------------------------------------

@requires_mode(FACE)
@permission_required("checkin.add_faceprofile")
def face_enroll(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == "POST":
        try:
            descriptors = json.loads(request.POST.get("descriptors", "[]"))
            enroll_face(member, descriptors if isinstance(descriptors, list) else [], request.user)
        except ConsentRequired as exc:
            messages.error(request, str(exc))
        except ValueError as exc:
            messages.error(request, str(exc) if "pictures" in str(exc) else "The face pictures could not be read. Please try again.")
            return redirect("checkin:face_enroll", member_id=member.pk)
        else:
            messages.success(request, f"{member.display_name}'s face is enrolled. They can now check in by looking at the kiosk.")
        return redirect(member)
    if not has_consent(member):
        messages.error(request, "Record the member's signed consent first (RA 10173).")
        return redirect(member)
    return render(request, "checkin/face_enroll.html", {"member": member})


@requires_mode(FACE)
@permission_required("checkin.delete_faceprofile")
@require_POST
def face_remove(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    FaceProfile.objects.filter(member=member).delete()
    messages.success(request, f"{member.display_name}'s face was removed. The kiosk will no longer recognise them.")
    return redirect(member)


# --- QR cards & stickers -------------------------------------------------------------------------

@requires_mode(QR)
@permission_required("checkin.add_checkincard")
@require_POST
def issue(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    had_card = hasattr(member, "checkin_card")
    issue_card(member, request.user)
    if had_card:
        messages.success(request, f"New QR code for {member.display_name}. The old sticker no longer works; print a new one.")
    else:
        messages.success(request, f"{member.display_name} has a QR code. Print their sticker.")
    return redirect(member)


@requires_mode(QR)
@permission_required("checkin.delete_checkincard")
@require_POST
def revoke(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    CheckinCard.objects.filter(member=member).delete()
    messages.success(request, f"{member.display_name}'s QR code was removed. Their sticker no longer works.")
    return redirect(member)


@requires_mode(QR)
@permission_required("checkin.view_checkincard")
def qr_image(request, member_id):
    card = get_object_or_404(CheckinCard, member_id=member_id)
    resp = HttpResponse(qr_svg(card.qr_text, scale=8, standalone=True), content_type="image/svg+xml")
    resp["Cache-Control"] = "private, no-store"
    return resp


def _sticker_people(request):
    """People for the sticker sheet: picked one by one (?member=), a household, or by status."""
    people = Member.objects.select_related("checkin_card").order_by("last_name", "first_name")
    ids = [i for i in request.GET.getlist("member") if i.isdigit()]
    if ids:
        return people.filter(pk__in=ids), {}
    filters = {
        "household": request.GET.get("household", ""),
        "status": request.GET.get("status", "active"),
        "show": request.GET.get("show", "unprinted"),
    }
    if filters["household"].isdigit():
        people = people.filter(household_id=filters["household"])
    if filters["status"] == "active":
        people = people.filter(status__in=Member.ACTIVE_STATUSES)
    elif filters["status"] in Member.Status.values:
        people = people.filter(status=filters["status"])
    if filters["show"] == "unprinted":
        people = people.exclude(checkin_card__printed_at__isnull=False)
    return people, filters


@requires_mode(QR)
@permission_required("checkin.view_checkincard")
def stickers(request):
    people, filters = _sticker_people(request)
    people = list(people)
    with_card = [m for m in people if hasattr(m, "checkin_card")]
    for m in with_card:
        m.qr = mark_safe(qr_svg(m.checkin_card.qr_text, scale=3))  # noqa: S308 - segno output, no user input
    return render(request, "checkin/stickers.html", {
        "people": with_card,
        "without_card": [m for m in people if not hasattr(m, "checkin_card")],
        "filters": filters,
        "picked": not filters,
        "households": Household.objects.order_by("name"),
        "statuses": Member.Status.choices,
    })


@requires_mode(QR)
@permission_required("checkin.add_checkincard")
@require_POST
def issue_many(request):
    members = Member.objects.filter(pk__in=request.POST.getlist("member"), checkin_card__isnull=True)
    count = 0
    for member in members:
        issue_card(member, request.user)
        count += 1
    messages.success(request, f"Gave QR codes to {count} {'person' if count == 1 else 'people'}.")
    return redirect(request.POST.get("next") or "checkin:stickers")


@requires_mode(QR)
@permission_required("checkin.change_checkincard")
@require_POST
def mark_printed(request):
    CheckinCard.objects.filter(member_id__in=request.POST.getlist("member")).update(printed_at=timezone.now())
    return HttpResponse(status=204)
