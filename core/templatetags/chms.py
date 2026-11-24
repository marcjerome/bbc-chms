from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_active(context, prefix, exclude=None):
    """'active' when the URL path starts with prefix ('/' matches exactly) and not with exclude."""
    path = context["request"].path
    if prefix == "/":
        return "active" if path == "/" else ""
    if exclude and path.startswith(exclude):
        return ""
    return "active" if path.startswith(prefix) else ""


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


@register.filter
def percent(part, whole):
    try:
        return min(100, round(part / whole * 100))
    except (TypeError, ZeroDivisionError):
        return 0


@register.simple_tag(takes_context=True)
def query_with(context, **kwargs):
    """Current querystring with some keys replaced, e.g. for pagination links."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
