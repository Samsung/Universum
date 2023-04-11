import argparse
import difflib
import glob
import json
import os
import pathlib
import shutil
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


def normalize(file: str) -> pathlib.Path:
    file_path = pathlib.Path(file)
    return file_path if file_path.is_absolute() else pathlib.Path.cwd().joinpath(file_path)


class HtmlDiffFileWriter:

    def __init__(self, target_folder: pathlib.Path, wrapcolumn: int, tabsize: int) -> None:
        self.target_folder = target_folder
        self.differ = difflib.HtmlDiff(tabsize=tabsize, wrapcolumn=wrapcolumn)

    def __call__(self, file: pathlib.Path, src: List[str], target: List[str]) -> None:
        file_relative = file.relative_to(pathlib.Path.cwd())
        out_file_name: str = str(file_relative).replace('/', '_') + '.html'
        with open(self.target_folder.joinpath(out_file_name), 'w', encoding="utf-8") as out_file:
            out_file.write(self.differ.make_file(src, target, context=False))


def diff_analyzer_output_parser(files: List[Tuple[pathlib.Path, pathlib.Path]],
                                write_diff_file: Optional[Callable[[pathlib.Path, List[str], List[str]], None]]
                                ) -> List[ReportData]:
    result: List[ReportData] = []
    for src_file, dst_file in files:
        with open(src_file, encoding="utf-8") as src:
            src_lines = src.readlines()
        with open(dst_file, encoding="utf-8") as fixed:
            fixed_lines = fixed.readlines()

        issues = _get_issues_from_diff(src_file, src_lines, fixed_lines)
        if issues and write_diff_file:
            write_diff_file(src_file, src_lines, fixed_lines)
        result.extend(issues)
    return result


def _get_issues_from_diff(src_file: pathlib.Path, src: List[str], target: List[str]) -> List[ReportData]:
    result = []
    matching_blocks: List[difflib.Match] = \
        difflib.SequenceMatcher(a=src, b=target).get_matching_blocks()
    previous_match = matching_blocks[0]
    for match in matching_blocks[1:]:
        block = _get_mismatching_block(previous_match, match, src, target)
        previous_match = match
        if not block:
            continue
        line, before, after = block
        path: pathlib.Path = src_file.relative_to(pathlib.Path.cwd())
        message = _get_issue_message(before, after)
        result.append(ReportData(
            symbol="Code Style issue",
            message=message,
            path=str(path),
            line=line
        ))

    return result


def _get_issue_message(before: str, after: str) -> str:
    # The maximum number of lines to write separate comments for
    # If exceeded, summarized comment will be provided instead
    max_lines = 11
    diff_size = len(before.splitlines())
    if diff_size > max_lines:
        message = f"\nLarge block of code ({diff_size} lines) has issues\n" + \
                  f"Non-compliant code blocks exceeding {max_lines} lines are not reported\n"
    else:
        # Message with before&after
        message = f"\nOriginal code:\n```diff\n{before}```\n" + \
                  f"Fixed code:\n```diff\n{after}```\n"
    return message


def _get_mismatching_block(previous_match: difflib.Match,  # src[a:a+size] = target[b:b+size]
                           match: difflib.Match,
                           src: List[str], target: List[str]
                           ) -> Optional[Tuple[int, str, str]]:
    previous_match_end_in_src = previous_match.a + previous_match.size
    previous_match_end_in_target = previous_match.b + previous_match.size
    match_start_in_src = match.a
    match_start_in_target = match.b
    if previous_match_end_in_src == match_start_in_src:
        return None
    line = match_start_in_src
    before = _get_text_for_block(previous_match_end_in_src - 1, match_start_in_src, src)
    after = _get_text_for_block(previous_match_end_in_target - 1, match_start_in_target, target)
    return line, before, after


def _get_text_for_block(start: int, end: int, lines: List[str]) -> str:
    return _replace_invisible_symbols(''.join(lines[start: end]))


def _replace_invisible_symbols(line: str) -> str:
    for old_str, new_str in zip([" ", "\t", "\n"], ["\u00b7", "\u2192\u2192\u2192\u2192", "\u2193\u000a"]):
        line = line.replace(old_str, new_str)
    return line


def diff_analyzer_argument_parser(description: str, module_path: str, output_directory: str) -> argparse.ArgumentParser:
    parser = create_parser(description, module_path)
    parser.add_argument("--output-directory", "-od", dest="output_directory", default=output_directory,
                        help=f"Directory to store fixed files and HTML files with diff; the default "
                             f"value is '{output_directory}'. Has to be distinct from source directory")
    parser.add_argument("--report-html", dest="write_html", action="store_true", default=False,
                        help="(optional) Set to generate html reports for each modified file")
    return parser


def diff_analyzer_common_main(settings: argparse.Namespace) -> None:
    settings.target_folder = normalize(settings.output_directory)
    if settings.target_folder.exists() and settings.target_folder.samefile(pathlib.Path.cwd()):
        raise EnvironmentError("Target folder must not be identical to source folder")

    settings.target_folder.mkdir(parents=True, exist_ok=True)

    if not shutil.which(settings.executable):
        raise EnvironmentError(f"{settings.name} executable '{settings.executable}' is not found. "
                               f"Please install {settings.name} or fix the executable name.")


def get_files_with_absolute_paths(settings: argparse.Namespace) -> Iterable[Tuple[pathlib.Path,
                                                                                  pathlib.Path,
                                                                                  pathlib.Path]]:
    for src_file in settings.file_list:
        src_file_absolute = normalize(src_file)
        src_file_relative = src_file_absolute.relative_to(pathlib.Path.cwd())
        target_file_absolute: pathlib.Path = settings.target_folder.joinpath(src_file_relative)
        yield src_file_absolute, target_file_absolute, src_file_relative
