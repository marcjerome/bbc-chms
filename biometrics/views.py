from datetime import datetime

from django import forms
from django.contrib import messages
from core.permissions import permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from members.models import Member

from .feature import requires_terminals
from .models import Consent, Device, Identity, Scan
from .services import ConsentRequired, ingest_attlog, ingest_operlog, record_consent, register_identity, withdraw_consent

SIMULATOR_SN = "SIMULATOR-01"


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "location", "is_active"]
        labels = {"is_active": "Approved (accept scans)"}


def _stats():
    return {
        "consented": Consent.objects.filter(withdrawn_on__isnull=True).count(),
        "registered": Identity.objects.count(),
        "enrolled": Identity.objects.filter(has_fingerprint=True).count()
        + Identity.objects.filter(has_fingerprint=False, has_face=True).count(),
        "active_people": Member.objects.filter(status__in=Member.ACTIVE_STATUSES).count(),
    }


@requires_terminals
@permission_required("biometrics.view_scan")
def overview(request):
    context = {"devices": Device.objects.all(), "scans": Scan.objects.select_related("member", "service__service_type", "device")[:25], **_stats()}
    template = "biometrics/overview.html#scan_feed" if request.htmx else "biometrics/overview.html"
    return render(request, template, context)


@requires_terminals
@permission_required("biometrics.change_device")
def device_update(request, pk):
    device = get_object_or_404(Device, pk=pk)
    form = DeviceForm(request.POST or None, instance=device)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{device} was saved.")
        return redirect("biometrics:overview")
    return render(request, "biometrics/device_form.html", {"form": form, "device": device})


@requires_terminals
@permission_required("biometrics.add_consent")
@require_POST
def consent(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    record_consent(member, request.user, request.POST.get("form_reference", "").strip())
    messages.success(request, f"Consent recorded for {member.display_name}.")
    return redirect(member)


@requires_terminals
@permission_required("biometrics.add_identity")
@require_POST
def register(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    try:
        identity = register_identity(member)
        messages.success(request, f"{member.display_name} is device user #{identity.pin}. Enroll their finger or face at the terminal.")
    except ConsentRequired as exc:
        messages.error(request, str(exc))
    return redirect(member)


@requires_terminals
@permission_required("biometrics.change_consent")
@require_POST
def withdraw(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    withdraw_consent(member)
    messages.success(request, f"Consent withdrawn. {member.display_name}'s face was removed from the kiosk, and they are being removed from all terminals.")
    return redirect(member)


# --- Simulator: lets you demo the full flow without hardware -----------------------------------

def simulator_device():
    device, _ = Device.objects.get_or_create(
        serial_number=SIMULATOR_SN, defaults={"name": "Simulator (demo)", "location": "Main door", "is_active": True}
    )
    return device


@requires_terminals
@permission_required("biometrics.change_device")
def simulator(request):
    device = simulator_device()
    identities = Identity.objects.select_related("member").order_by("member__last_name", "member__first_name")
    result = None
    if request.method == "POST":
        action = request.POST.get("action")
        identity = identities.filter(pk=request.POST.get("identity") or 0).first()
        try:
            when = timezone.make_aware(datetime.fromisoformat(request.POST.get("when", "")))
        except ValueError:
            when = timezone.now()
        stamp = timezone.localtime(when).strftime("%Y-%m-%d %H:%M:%S")
        if action == "enroll" and identity:
            # Same notice a real terminal pushes after a finger is registered on it.
            ingest_operlog(device, f"FP PIN={identity.pin}\tFID=6\tSize=1024\tValid=1\tTMP=(discarded)")
            identity.refresh_from_db()
            result = {"kind": "enrolled", "identity": identity}
        else:
            pin = "99999" if action == "unknown" else (identity.pin if identity else "")
            verify = "15" if action == "face" else "1"
            # Same ATTLOG line format a real terminal pushes: PIN, time, status, verify mode.
            scans = ingest_attlog(device, f"{pin}\t{stamp}\t0\t{verify}\t0\t0") if pin else []
            result = {"kind": "scan", "scan": scans[0] if scans else None}
        if request.htmx:
            return render(request, "biometrics/simulator.html#screen", {"result": result})
    return render(request, "biometrics/simulator.html", {
        "device": device, "identities": identities, "result": result,
        "now": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
    })
