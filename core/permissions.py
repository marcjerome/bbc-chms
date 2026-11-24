from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required as django_permission_required


def permission_required(perm):
    """
    Signed out: go to the login page. Signed in without the permission: a "no access" page (403).
    Django's own decorator sends both to the login page, which bounces a signed-in user straight
    back, so the browser ends in "too many redirects".
    """
    def decorator(view):
        return login_required(django_permission_required(perm, raise_exception=True)(view))
    return decorator
