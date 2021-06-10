import argparse
from lxml import etree
import sys

from typing import List

from . import utils


def main() -> int:
    settings = scan_build_report_argument_parser().parse_args()
    files = utils.expand_files_argument(settings)
    return utils.report_parsed_outcome(None,
                                       lambda _: scan_build_report_output_parser(files),
                                       settings.result_file)


def scan_build_report_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse scan-build report")
    utils.add_files_argument(parser)
    utils.add_result_file_argument(parser)
    return parser


def scan_build_report_output_parser(file_list: List[str]) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for report_file in file_list:
        with open(report_file) as f:
            parser = etree.HTMLParser()
            tree: etree.ElementTree = etree.parse(f, parser)
            found = any(x.text for x in tree.iter() if x.text == 'Bug Summary')
            if not found:
                continue
            table_data = [x.getchildren() for x in tree.iter(tag='table')][0]
            row_path = list(table_data[0])
            row_issue = list(table_data[1])
            if row_path[0].text != 'File:' or row_issue[0].text != 'Warning:':
                raise ValueError("Wrong format of file: " + f.name)

            issue_data = list(row_issue)[1]
            line_data = list(issue_data)[0].text  # 'line 1, column 1'
            result.append(utils.ReportData(
                symbol="Reported issue",
                message=list(issue_data)[1].tail,
                path=row_path[1].text,
                line=int(line_data.split(',')[0][5:]))
            )
    return result


if __name__ == "__main__":
    sys.exit(main())
