import argparse
import glob
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Callable, List, Optional, Tuple, Set, Iterable

from typing_extensions import TypedDict

from universum.lib.ci_exception import CiException

ReportData = TypedDict('ReportData', {'path': str, 'message': str, 'symbol': str, 'line': int})


class AnalyzerException(CiException):
    def __init__(self, code: int = 2, message: Optional[str] = None):
        self.code: int = code
        self.message: Optional[str] = message


def create_parser(description: str, module_path: str) -> argparse.ArgumentParser:
    module_name, _ = os.path.splitext(os.path.basename(module_path))

    prog = f"python{sys.version_info.major}.{sys.version_info.minor} -m {__package__}.{module_name}"
    return argparse.ArgumentParser(prog=prog, description=description)


def analyzer(parser: argparse.ArgumentParser):
    """
    Wraps the analyzer specific data and adds common protocol information:
      --files argument and its processing
      --result-file argument and its processing
    This function exists to define analyzer report interface

    :param parser: Definition of analyzer custom arguments
    :return: Wrapped analyzer with common reporting behaviour
    """

    def internal(func: Callable[[argparse.Namespace], List[ReportData]]) -> Callable[[], List[ReportData]]:
        def wrapper() -> List[ReportData]:
            add_files_argument(parser)
            add_result_file_argument(parser)
            settings: argparse.Namespace = parser.parse_args()
            expand_files_argument(settings)
            issues: List[ReportData] = func(settings)
            report_to_file(issues, settings.result_file)
            return issues

        return wrapper

    return internal


def sys_exit(func: Callable[[], Any]) -> Callable[[], None]:
    """
    Execute target function, wrapping any generated exceptions and reporting them to system output
    Exit with code 0, if target function generates no output
    Exit with code 1, if target function generates any outputs, but executes normally
    Exit with code 2 (or custom), if target function fails with an exception

    This decorator is used for analyzer modules to provide normal script interface
    Note: while debugging, remove it from the analyzer code to see the full error state

    :param func: Target function to execute
    :return: None

    >>> def _raise_common() -> None:
    ...     raise Exception()
    >>> def _raise_custom() -> None:
    ...     raise AnalyzerException(code=3)
    >>> def wrap_system_exit(f: Callable) -> int:
    ...     try:
    ...         f()
    ...     except SystemExit as se:
    ...         return se.code
    >>> wrap_system_exit(sys_exit(lambda: None))
    0
    >>> wrap_system_exit(sys_exit(lambda: 'pass'))
    1
    >>> wrap_system_exit(sys_exit(_raise_common))
    2
    >>> wrap_system_exit(sys_exit(_raise_custom))
    3
    """

    def wrapper() -> None:
        exit_code: int
        try:
            res = func()
            exit_code = 1 if res else 0
        except Exception as e:
            message: Optional[str] = getattr(e, 'message', None)
            exit_code = getattr(e, 'code', 2)
            if message:
                sys.stderr.write(message)
            else:
                sys.stderr.write(str(e))
        sys.exit(exit_code)

    return wrapper


def run_for_output(cmd: List[str]) -> Tuple[str, str]:
    result = subprocess.run(cmd, universal_newlines=True,  # pylint: disable=subprocess-run-check
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stderr and not result.stdout:
        raise AnalyzerException(code=result.returncode, message=result.stderr)

    return result.stdout, result.stderr


def add_files_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--files", dest="file_list", nargs='+', required=True,
                        help="Target file or directory; accepts multiple values; ")


def expand_files_argument(settings: argparse.Namespace) -> None:
    # TODO: subclass argparse.Action
    result: Set[str] = set()
    for pattern in settings.file_list:
        file_list: List[str] = glob.glob(pattern)
        if not file_list:
            sys.stderr.write(f"Warning: no files found for input pattern {pattern}\n")
        else:
            result.update(file_list)

    if not result:
        raise AnalyzerException(message="Error: no files found for analysis\n")

    settings.file_list = list(result)


def add_result_file_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--result-file", dest="result_file", required=True,
                        help="File for storing json results of Universum run. Set it to \"${CODE_REPORT_FILE}\" "
                             "for running from Universum, variable will be handled during run. If you run this "
                             "script separately from Universum, just name the result file or leave it empty.")


def add_python_version_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--python-version", dest="version", default="3",
                        help="Version of the python interpreter, such as 2, 3 or 3.7. "
                             "Pylint analyzer uses this parameter to select python binary for launching pylint. "
                             "For example, if the version is 3.7, it uses the following command: "
                             "'python3.7 -m pylint <...>'")


def report_to_file(issues: List[ReportData], json_file: Optional[str] = None) -> None:
    issues_json = json.dumps(issues, indent=4)
    if json_file:
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(issues_json)
    else:
        sys.stdout.write(issues_json)


def normalize_path(file: str) -> pathlib.Path:
    file_path = pathlib.Path(file)
    return file_path if file_path.is_absolute() else pathlib.Path.cwd().joinpath(file_path)


def get_files_with_absolute_paths(settings: argparse.Namespace) -> Iterable[Tuple[pathlib.Path,
                                                                                  pathlib.Path,
                                                                                  pathlib.Path]]:
    for src_file in settings.file_list:
        src_file_absolute = normalize_path(src_file)
        src_file_relative = src_file_absolute.relative_to(pathlib.Path.cwd())
        target_file_absolute: pathlib.Path = settings.target_folder.joinpath(src_file_relative)
        yield src_file_absolute, target_file_absolute, src_file_relative
