import json
import sys


def add_common_arguments(parser):
    parser.add_argument("--result-file", dest="result_file",
                        help="File for storing json results of Universum run. Set it to \"${CODE_REPORT_FILE}\" "
                             "for running from Universum, variable will be handled during run. If you run this "
                             "script separately from Universum, just name the result file or leave it empty.")


def analyzers_output(json_file: str, issues_loads) -> None:
    issues = json.dumps(issues_loads, indent=4)
    if json_file:
        open(json_file, "w").write(issues)
    else:
        sys.stdout.write(issues)
