"""
On-premise host check. The church computer gets its address from the router, so instead of listing
every possible IP in ALLOWED_HOSTS, accept any private network address (192.168.x.x, 10.x.x.x,
172.16-31.x.x), localhost and *.local names, plus whatever ALLOWED_HOSTS lists (e.g. a domain).
Anything else, such as a public IP or a stranger's domain pointed at us, gets a 400.
"""

import ipaddress

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.http.request import split_domain_port, validate_host


def is_private_network_host(domain):
    if domain == "localhost" or domain.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(domain.strip("[]"))
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


class PrivateNetworkHostMiddleware:
    """Used when PRIVATE_NETWORK_HOSTS is on; ALLOWED_HOSTS is then '*' and this does the checking."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        domain, _port = split_domain_port(request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", ""))
        if not domain or not (
            is_private_network_host(domain) or validate_host(domain, settings.LISTED_HOSTS)
        ):
            return HttpResponseBadRequest("This address is not allowed. Use the church computer's network address.")
        return self.get_response(request)
