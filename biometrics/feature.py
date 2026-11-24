"""Door terminals are on when the Fingerprint or Face check-in mode is on (checkin.feature)."""

from checkin.feature import FACE, FINGERPRINT, requires_mode, terminals_on

requires_terminals = requires_mode(FINGERPRINT, FACE)

__all__ = ["requires_terminals", "terminals_on"]
