class LoginError(RuntimeError):
    """Raised when authentication with the grinder fails."""


class ProtocolError(RuntimeError):
    """Raised when an unknown or malformed frame is received."""
