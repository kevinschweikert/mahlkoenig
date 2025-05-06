class GrinderError(Exception):
    """Base exception for all grinder errors."""

    pass


class AuthenticationError(GrinderError):
    """Raised when authentication with the grinder fails."""

    pass


class ProtocolError(GrinderError):
    """Raised when an unknown or malformed frame is received."""

    pass


class ConnectionError(GrinderError):
    """Error establishing connection to the grinder."""

    pass
