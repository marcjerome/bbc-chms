"""
Minimal server side of the ZKTeco ADMS ("push"/iclock) protocol, which ZKTeco-class terminals
speak over plain HTTP. Point the device's Cloud/ADMS server setting at this site.

  GET  /iclock/cdata?SN=..           handshake -> options
  POST /iclock/cdata?SN=..&table=..  ATTLOG (scans) / OPERLOG (enrollment notices)
  GET  /iclock/getrequest?SN=..      device polls for queued commands
  POST /iclock/devicecmd?SN=..       device reports command results
"""

from django.http import Http404, HttpResponse, QueryDict
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .feature import terminals_on
from .models import Device, DeviceCommand
from .services import ingest_attlog, ingest_operlog

MAX_COMMANDS_PER_POLL = 10


def text(body):
    return HttpResponse(body, content_type="text/plain")


def _device(request):
    if not terminals_on():
        raise Http404
    sn = request.GET.get("SN", "").strip()
    if not sn:
        raise Http404
    device, _ = Device.objects.get_or_create(serial_number=sn)  # unknown devices await approval
    Device.objects.filter(pk=device.pk).update(
        last_seen=timezone.now(), last_ip=request.META.get("REMOTE_ADDR")
    )
    return device


@csrf_exempt
def cdata(request):
    device = _device(request)
    if request.method == "GET":
        return text("\n".join([
            f"GET OPTION FROM: {device.serial_number}",
            "ATTLOGStamp=None", "OPERLOGStamp=9999", "ATTPHOTOStamp=None",
            "ErrorDelay=30", "Delay=10", "TransTimes=00:00;14:05", "TransInterval=1",
            "TransFlag=TransData AttLog OpLog EnrollUser EnrollFP FACE",
            "TimeZone=8", "Realtime=1", "Encrypt=None",
        ]))
    body = request.body.decode("utf-8", errors="replace")
    table = request.GET.get("table", "")
    if table == "ATTLOG":
        return text(f"OK: {len(ingest_attlog(device, body))}")
    if table in ("OPERLOG", "BIODATA"):
        ingest_operlog(device, body)
    return text(f"OK: {len(body.splitlines())}")


def getrequest(request):
    device = _device(request)
    if not device.is_active:
        return text("OK")
    commands = list(device.commands.filter(status=DeviceCommand.Status.PENDING)[:MAX_COMMANDS_PER_POLL])
    if not commands:
        return text("OK")
    DeviceCommand.objects.filter(pk__in=[c.pk for c in commands]).update(
        status=DeviceCommand.Status.SENT, sent_at=timezone.now()
    )
    return text("\n".join(f"C:{c.pk}:{c.command}" for c in commands) + "\n")


@csrf_exempt
def devicecmd(request):
    device = _device(request)
    for line in request.body.decode("utf-8", errors="replace").splitlines():
        result = QueryDict(line)
        if result.get("ID", "").isdigit():
            ok = result.get("Return") == "0"
            device.commands.filter(pk=int(result["ID"])).update(
                status=DeviceCommand.Status.DONE if ok else DeviceCommand.Status.FAILED,
                return_code=result.get("Return", ""),
            )
    return text("OK")
