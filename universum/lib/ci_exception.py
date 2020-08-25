__all__ = [
    "CiException",
    "CriticalCiException",
    "SilentAbortException",
    "StepException"
]


class CiException(Exception):
    pass


class CriticalCiException(Exception):
    pass


class SilentAbortException(Exception):
    def __init__(self, application_exit_code=1):
        super().__init__()
        self.application_exit_code = application_exit_code


class StepException(Exception):
    pass
