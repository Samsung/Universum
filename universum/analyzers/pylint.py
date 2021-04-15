import argparse
import json
import sys

from typing import List

from . import utils


def form_arguments_for_documentation() -> argparse.ArgumentParser:
    return _pylint_argument_parser()


def main() -> int:
    settings: argparse.Namespace = _pylint_argument_parser().parse_args()

    cmd = [f"python{settings.version}", '-m', 'pylint', '-f', 'json']
    if settings.rcfile:
        cmd.append(f'--rcfile={settings.rcfile}')
    cmd.extend(utils.expand_files_argument(settings))

    return utils.report_parsed_outcome(cmd, _pylint_output_parser, settings.result_file)


def _pylint_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pylint analyzer")
    utils.add_files_argument(parser)
    parser.add_argument("--rcfile", dest="rcfile", type=str, help="Specify a configuration file.")
    utils.add_python_version_argument(parser)
    utils.add_result_file_argument(parser)
    return parser


def _pylint_output_parser(output: str) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for data in json.loads(output):
        # pylint has its own escape rules for json output of "message" values.
        # it uses cgi.escape lib and escapes symbols <>&
        result.append(utils.ReportData(
            symbol=data["symbol"],
            message=data["message"].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"),
            path=data["path"],
            line=int(data["line"])
        ))
    return result


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
