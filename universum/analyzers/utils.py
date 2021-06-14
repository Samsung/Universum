import json
import sys
import argparse
import glob
import subprocess

from typing import Any, Callable, List, Optional, Tuple
from typing_extensions import TypedDict

from universum.lib.ci_exception import CiException

ReportData = TypedDict('ReportData', {'path': str, 'message': str, 'symbol': str, 'line': int})


class AnalyzerException(CiException):
    def __init__(self, code: int = 2, message: Optional[str] = None):
        self.code: int = code
        self.message: Optional[str] = message


def analyzer(parser: argparse.ArgumentParser):
    def internal(func: Callable[[argparse.Namespace], List[ReportData]]) -> Callable[[], List[ReportData]]:
        def wrapper() -> List[ReportData]:
            add_result_file_argument(parser)
            settings: argparse.Namespace = parser.parse_args()
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
        sys.exit(exit_code)

    return wrapper


def run_for_output(cmd: List[str]) -> Tuple[str, str]:
    result = subprocess.run(cmd, universal_newlines=True,  # pylint: disable=subprocess-run-check
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stderr and not result.stdout:
        raise AnalyzerException(code=result.returncode, message=result.stderr)

    return result.stdout, result.stderr


def add_files_argument(parser: argparse.ArgumentParser, is_required: bool = True) -> None:
    # TODO: refactor uncrustify to make 'file_list' arg as common as 'result_file'
    parser.add_argument("--files", dest="file_list", nargs='+' if is_required else '*', required=is_required,
                        default=None if is_required else [],
                        help="Target file or directory; accepts multiple values; ")


def expand_files_argument(settings: argparse.Namespace) -> List[str]:
    result = []
    for pattern in settings.file_list:
        result.extend(glob.glob(pattern))
    return result


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


def report_to_file(issues: List[ReportData], json_file: str = None) -> None:
    issues_json = json.dumps(issues, indent=4)
    if json_file:
        open(json_file, "w").write(issues_json)
    else:
        sys.stdout.write(issues_json)
