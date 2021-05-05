import json
import sys
import argparse
import glob
import subprocess

from typing import Callable, List
from typing_extensions import TypedDict

ReportData = TypedDict('ReportData', {'path': str, 'message': str, 'symbol': str, 'line': int})


def report_parsed_outcome(cmd: List[str],
                          parse_function: Callable[[str], List[ReportData]],
                          out_file: str) -> int:
    result = subprocess.run(cmd, universal_newlines=True,  # pylint: disable=subprocess-run-check
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stderr and not result.stdout:
        sys.stderr.write(result.stderr)
        return result.returncode

    try:
        parsed_issues = parse_function(result.stdout)
    except Exception as e:
        sys.stderr.write("Error encountered while parsing output:\n")
        sys.stderr.write(str(e))
        return 2

    output_report_to_file(parsed_issues, out_file)
    return 1 if parsed_issues else 0


def add_files_argument(parser: argparse.ArgumentParser, is_required: bool = True) -> None:
    parser.add_argument("--files", dest="file_list", nargs='+' if is_required else '*', required=is_required,
                        default=None if is_required else [],
                        help="File or directory to check; accepts multiple values; ")


def expand_files_argument(settings: argparse.Namespace) -> List[str]:
    result = []
    for pattern in settings.file_list:
        result.extend(glob.glob(pattern))
    return result


def add_result_file_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--result-file", dest="result_file",
                        help="File for storing json results of Universum run. Set it to \"${CODE_REPORT_FILE}\" "
                             "for running from Universum, variable will be handled during run. If you run this "
                             "script separately from Universum, just name the result file or leave it empty.")


def add_python_version_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--python-version", dest="version", default="3",
                        help="Version of the python interpreter, such as 2, 3 or 3.7. "
                             "Pylint analyzer uses this parameter to select python binary for launching pylint. "
                             "For example, if the version is 3.7, it uses the following command: "
                             "'python3.7 -m pylint <...>'")


def output_report_to_file(issues: List[ReportData], json_file: str = None) -> None:
    issues_json = json.dumps(issues, indent=4)
    if json_file:
        open(json_file, "w").write(issues_json)
    else:
        sys.stdout.write(issues_json)
