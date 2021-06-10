import argparse
import json
import sys

from typing import Dict, List

from . import utils


def form_arguments_for_documentation() -> argparse.ArgumentParser:
    return _direct_report_argument_parser()


def main() -> int:
    settings = _direct_report_argument_parser().parse_args()
    cmd = ['echo']  # shell nop
    return utils.report_parsed_outcome(cmd,
                                       lambda _: _direct_report_output_parser(settings.file_list),
                                       settings.result_file)


def _direct_report_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report pre-generated analysis")
    utils.add_files_argument(parser)
    utils.add_result_file_argument(parser)
    return parser


def _direct_report_output_parser(file_list: List[str]) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for report_file in file_list:
        with open(report_file) as f:
            json_data: List[Dict[str, str]] = json.load(f)
            for issue in json_data:
                result.append(utils.ReportData(
                    symbol="Reported issue",
                    message=issue["message"],
                    path=issue["path"],
                    line=int(issue["line"])
                ))
    return result


if __name__ == "__main__":
    sys.exit(main())
