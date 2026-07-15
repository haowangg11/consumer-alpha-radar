class SkillError(Exception):
    """
    Base class for all skill execution failures. Skills (and the
    shared HTTP helper) should raise this - or a subclass - instead
    of returning an error dict directly; SkillService is responsible
    for catching it and normalizing it into the error response shape.

    `retryable` tells callers whether re-issuing the same call is
    expected to help (e.g. a timeout) versus not (e.g. a 404 or a
    malformed payload).
    """

    retryable = False

    def __init__(self, message: str, *, retryable: bool | None = None):
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable


class SkillTimeoutError(SkillError):
    retryable = True


class SkillConnectionError(SkillError):
    retryable = True


class SkillHTTPError(SkillError):
    """Raised when an external API responds with a non-2xx status."""

    def __init__(self, message: str, *, status_code: int, retryable: bool = False):
        super().__init__(message, retryable=retryable)
        self.status_code = status_code


class SkillInvalidPayloadError(SkillError):
    """Raised when a skill is called with a payload it cannot use."""

    retryable = False
