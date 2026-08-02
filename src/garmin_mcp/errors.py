class GarminMcpError(RuntimeError):
    """Base error safe to surface through MCP."""


class AuthenticationRequired(GarminMcpError):
    """Raised when local Garmin tokens are missing or invalid."""


class UpstreamUnavailable(GarminMcpError):
    """Raised when Garmin is unavailable and no cached fallback exists."""


class InvalidRequest(GarminMcpError):
    """Raised when a tool request exceeds safety bounds."""

