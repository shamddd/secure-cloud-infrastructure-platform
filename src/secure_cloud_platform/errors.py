class PlatformError(Exception):
    """Base class for expected domain failures."""


class AuthenticationError(PlatformError):
    pass


class AuthorizationError(PlatformError):
    pass


class ConflictError(PlatformError):
    pass


class NotFoundError(PlatformError):
    pass
