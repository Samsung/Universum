import argparse
from typing import List
from lxml import etree

from . import utils


def scan_build_report_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse scan-build report")
    return parser


@utils.sys_exit
@utils.analyzer(scan_build_report_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    issues = scan_build_report_output_parser(settings.file_list)
    return issues


def scan_build_report_output_parser(file_list: List[str]) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for report_file in file_list:
        with open(report_file, encoding="utf-8") as f:
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
                line=int(line_data.split(',')[0][5:])
            ))
    return result


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter  # see https://github.com/PyCQA/pylint/issues/259
