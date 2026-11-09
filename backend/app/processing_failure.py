"""Evidence for a completed QA check that cannot produce an analysis artifact."""
from .pixel_policy import QualityError


class ProcessingBlocked(QualityError):
    def __init__(self, message, failure):
        super().__init__(message)
        self.failure = failure
