from typing import List
import inspect

from ..lib.gravity import Module, Dependency


class GlobalErrorState(Module):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.errors: List[str] = []

    def get_errors(self) -> List[str]:
        return self.errors

    def is_in_error_state(self) -> bool:
        return len(self.errors) > 0


class HasErrorState(Module):
    global_error_state_factory = Dependency(GlobalErrorState)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.global_error_state: GlobalErrorState = self.global_error_state_factory()

    def error(self, message: str) -> None:
        self.global_error_state.errors.append(inspect.cleandoc(message))

    def is_in_error_state(self) -> bool:
        return self.global_error_state.is_in_error_state()

    def check_required_option(self, setting_name: str, message: str) -> bool:
        if not getattr(self.settings, setting_name, None):
            self.error(message)
            return False
        return True

    def read_multiline_option(self, setting_name: str) -> str:
        value: str = getattr(self.settings, setting_name, None)
        if not value:
            return ""
        if value.startswith('@'):
            try:
                with open(value.lstrip('@')) as value_file:
                    return value_file.read()
            except FileNotFoundError as e:
                self.error(f"Error reading argument {setting_name} from file {e.filename}: no such file")
                return ""
        return value

    def read_and_check_multiline_option(self, setting_name: str, error_message: str) -> str:
        result = self.read_multiline_option(setting_name)
        if not result:
            self.error(error_message)
            return ""

        return result
