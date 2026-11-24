import re

from django.core.exceptions import ValidationError

PHONE_CHARS = re.compile(r"^\+?[\d\s().-]+$")


def validate_phone(value):
    """A phone number: digits with optional +, spaces, dashes, dots or brackets; 7 to 15 digits."""
    digits = re.sub(r"\D", "", value)
    if not PHONE_CHARS.match(value) or not 7 <= len(digits) <= 15:
        raise ValidationError("Enter a phone number, e.g. 0917 123 4567 or +63 917 123 4567.")
