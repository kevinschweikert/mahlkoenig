class MahlkoenigError(Exception):
    """Base exception for all grinder errors."""

    pass


class MahlkoenigAuthenticationError(MahlkoenigError):
    """Raised when authentication with the grinder fails."""

    pass


class MahlkoenigProtocolError(MahlkoenigError):
    """Raised when an unknown or malformed frame is received."""

    pass


class MahlkoenigConnectionError(MahlkoenigError):
    """Error establishing connection to the grinder."""

    pass
