from typing import List

from ..lib.gravity import Module, Dependency


class GlobalErrorState(Module):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.errors: List[str] = []


class ErrorState(Module):
    global_error_state_factory = Dependency(GlobalErrorState)

    def __init__(self, *args, **kwargs) -> None:
        # mypy doesn't support cooperative inheritance
        super().__init__(*args, **kwargs)  # type: ignore
        self.global_error_state = self.global_error_state_factory()

    def error(self, message: str):
        self.global_error_state.errors.append(message)

    def is_error_state(self):
        return len(self.global_error_state.errors) > 0

    def get_errors(self):
        return self.global_error_state.errors
