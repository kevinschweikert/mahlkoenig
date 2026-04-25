class MahlkoenigError(Exception):
    """Base exception for all grinder errors."""

    pass


class MahlkoenigAuthenticationError(MahlkoenigError):
    """Raised when authentication with the grinder fails."""

    pass


class MahlkoenigProtocolError(MahlkoenigError):
    """Raised when an unknown or malformed frame is received."""

    def __init__(self, message: str, data: object = None) -> None:
        super().__init__(message)
        self.data = data

    def __str__(self) -> str:
        base_str = super().__str__()
        if self.data is not None:
            return f"{base_str} (received: {self.data!r})"
        return base_str


class MahlkoenigConnectionError(MahlkoenigError):
    """Error establishing or maintaining a connection to the grinder."""

    pass


class MahlkoenigTimeoutError(MahlkoenigConnectionError):
    """Raised when a request to the grinder does not complete in time."""

    pass
