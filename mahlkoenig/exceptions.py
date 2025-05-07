class MahlkoenigError(Exception):
    """Base exception for all grinder errors."""

    pass


class MahlkoenigAuthenticationError(MahlkoenigError):
    """Raised when authentication with the grinder fails."""

    pass


class MahlkoenigProtocolError(MahlkoenigError):
    """Raised when an unknown or malformed frame is received."""

    def __init__(self, message: str, data=None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.data = data  # Store the received message as an attribute

    def __str__(self):
        base_str = super().__str__()
        if self.data is not None:
            return f"{base_str} (received: {self.data!r})"
        return base_str


class MahlkoenigConnectionError(MahlkoenigError):
    """Error establishing connection to the grinder."""

    pass
