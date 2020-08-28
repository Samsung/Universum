from typing import Any, Callable, List, Optional, TypeVar, Union
from types import TracebackType
import inspect
import os
import sys
import traceback

import requests
from requests.models import Response

from .ci_exception import CiException, CriticalCiException, SilentAbortException
from .module_arguments import IncorrectParameterError
from .gravity import Module, HasModulesMapping

__all__ = [
    "strip_path_start",
    "parse_path",
    "calculate_file_absolute_path",
    "detect_environment",
    "create_driver",
    "format_traceback",
    "check_required_option",
    "read_and_check_multiline_option",
    "catch_exception",
    "trim_and_convert_to_unicode",
    "convert_to_str",
    "unify_argument_list",
    "Uninterruptible",
    "make_block",
    "make_request"
]

ReturnT = TypeVar('ReturnT')
DecoratorT = Callable[[Callable[..., ReturnT]], Callable[..., ReturnT]]


def strip_path_start(line: str) -> str:
    if line.startswith("./"):
        return line[2:]
    return line


def parse_path(path: str, starting_point: str) -> str:
    if path.startswith('/'):
        path = os.path.join(path)
    else:
        path = os.path.join(starting_point, path)

    return os.path.abspath(path)


def calculate_file_absolute_path(target_directory: str, file_basename: str) -> str:
    name = file_basename.replace(" ", "_")
    name = name.replace("/", "\\")
    if name.startswith('_'):
        name = name[1:]
    return os.path.join(target_directory, name)


def detect_environment() -> str:
    """
    :return: "tc" if the script is launched on TeamCity agent,
             "jenkins" is launched on Jenkins agent,
             "terminal" otherwise
    """
    teamcity = "TEAMCITY_VERSION" in os.environ
    jenkins = "JENKINS_HOME" in os.environ
    pycharm = "PYCHARM_HOSTED" in os.environ
    if pycharm:
        return "terminal"
    if teamcity and not jenkins:
        return "tc"
    if not teamcity and jenkins:
        return "jenkins"
    return "terminal"


LocalFactoryT = TypeVar('LocalFactoryT', bound=Module)
TeamcityFactoryT = TypeVar('TeamcityFactoryT', bound=Module)
JenkinsFactoryT = TypeVar('JenkinsFactoryT', bound=Module)


def create_driver(local_factory: Callable[[], LocalFactoryT],
                  teamcity_factory: Callable[[], TeamcityFactoryT],
                  jenkins_factory: Callable[[], JenkinsFactoryT],
                  env_type: str = "") -> Union[LocalFactoryT, TeamcityFactoryT, JenkinsFactoryT]:
    if not env_type:
        env_type = detect_environment()

    if env_type == "tc":
        return teamcity_factory()
    if env_type == "jenkins":
        return jenkins_factory()
    return local_factory()


def format_traceback(exc: Exception, trace: Optional[TracebackType]) -> str:
    tb_lines: List[str] = traceback.format_exception(exc.__class__, exc, trace)
    tb_text: str = ''.join(tb_lines)
    return tb_text


def check_required_option(settings: HasModulesMapping, setting_name: str, error_message: str) -> None:
    if not getattr(settings, setting_name, None):
        raise IncorrectParameterError(inspect.cleandoc(error_message))


def read_and_check_multiline_option(settings: HasModulesMapping, setting_name: str, error_message: str) -> str:
    try:
        value: str = getattr(settings, setting_name, None)
        if value.startswith('@'):
            try:
                with open(value.lstrip('@')) as file_name:
                    result = file_name.read()
            except FileNotFoundError as e:
                raise IncorrectParameterError(f"Error reading argument {setting_name} from file {e.filename}: no such "
                                              f"file") from e
        elif value == '-':
            result = "".join(sys.stdin.readlines())
        else:
            result = value
    except AttributeError as e:
        raise IncorrectParameterError(inspect.cleandoc(error_message)) from e

    if not result:
        raise IncorrectParameterError(inspect.cleandoc(error_message))

    return result


def catch_exception(exception_name: str, ignore_if: str = None) -> DecoratorT:
    def decorated_function(function):
        def function_to_run(*args, **kwargs):
            result: ReturnT = None
            try:
                result = function(*args, **kwargs)
                return result
            except Exception as e:
                if not type(e).__name__ == exception_name:
                    raise
                if ignore_if is not None:
                    if ignore_if in str(e):
                        return result
                raise CriticalCiException(str(e)) from e
        return function_to_run
    return decorated_function


def trim_and_convert_to_unicode(line: Union[bytes, str]) -> str:
    if not isinstance(line, str):
        line = str(line)

    if line.endswith("\n"):
        line = line[:-1]

    return line


def convert_to_str(line: Union[bytes, str]) -> str:
    if isinstance(line, bytes):
        return line.decode("utf8", "replace")
    return str(line)


def unify_argument_list(source_list: Optional[List[str]], separator: str = ',',
                        additional_list: Optional[List[str]] = None) -> List[str]:
    resulting_list: List[str] = additional_list if additional_list else []

    # Add arguments parsed by ModuleArgumentParser, including list elements generated by nargs='+'
    if source_list is not None:
        for item in source_list:
            if isinstance(item, list):
                resulting_list.extend(item)
            else:
                resulting_list.append(item)

    # Remove None and empty elements added by previous steps
    resulting_list = [item for item in resulting_list if item]

    # Split one-element arguments and merge to one list
    resulting_list = [item.strip() for entry in resulting_list for item in entry.strip('"\'').split(separator)]

    return resulting_list


class Uninterruptible:
    def __init__(self, error_logger: Callable[[str], None]) -> None:
        self.return_code: int = 0
        self.error_logger: Callable[[str], None] = error_logger
        self.exceptions: List[str] = []

    def __enter__(self) -> Callable[..., None]:
        def excepted_function(func: Callable[..., None], *args, **kwargs):
            try:
                func(*args, **kwargs)
            except SilentAbortException as e:
                self.return_code = max(self.return_code, e.application_exit_code)
            except (KeyboardInterrupt, SystemExit):
                self.error_logger("Interrupted from outer scope\n")
                self.return_code = 3
            except Exception as e:
                ex_traceback = sys.exc_info()[2]
                self.exceptions.append(format_traceback(e, ex_traceback))
                self.return_code = max(self.return_code, 2)
        return excepted_function

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.return_code == 2:
            for entry in self.exceptions:
                sys.stderr.write(entry)
        if self.return_code != 0:
            raise SilentAbortException(application_exit_code=self.return_code)


def make_block(block_name: str, pass_errors: bool = True) -> DecoratorT:
    def decorated_function(func):
        def function_in_block(self, *args, **kwargs):
            return self.structure.run_in_block(func, block_name, pass_errors, self, *args, **kwargs)
        return function_in_block
    return decorated_function


def make_request(url: str, request_method: str = "GET", critical: bool = True, **kwargs) -> Response:
    try:
        response: Response = requests.request(method=request_method, url=url, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        text = f"Error opening URL, got '{type(error).__name__}' with following message:\n{error}"
        if critical:
            raise CriticalCiException(text) from error
        raise CiException(text) from error
