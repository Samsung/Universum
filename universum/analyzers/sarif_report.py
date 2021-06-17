import argparse
import json
from typing import Any, Dict, List

from . import utils


def scan_build_report_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse SARIF report")
    return parser


@utils.sys_exit
@utils.analyzer(scan_build_report_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    issues = sarif_report_output_parser(settings.file_list)
    return issues


def sarif_report_output_parser(file_list: List[str]) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for report_file in file_list:
        with open(report_file, "r") as f:
            report = json.loads(f.read())
            try:
                result.extend(parse_sarif_json(report))
            except AttributeError as e:
                raise ValueError("Malformed SARIF file") from e
    return result


def parse_sarif_json(report: Dict[str, Any]) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    version: str = report.get('version', '')
    if version != '2.1.0':
        raise ValueError(f"Version {version} is not supported")
    for run in report.get('runs', []):
        analyzer_data: Dict[str, str] = run.get('tool').get('driver')  # non-optional per definition
        who: str = f"{analyzer_data.get('name')} [{analyzer_data.get('version', '?')}]"
        for issue in run.get('results', []):
            what: str = issue.get('message')
            for location in issue.get('locations', []):
                location_data: Dict[str, Dict[str, str]] = location.get('physicalLocation')
                if not location_data:
                    continue
                artifact_data = location_data.get('artifactLocation')
                if not artifact_data:
                    if location_data.get('address'):
                        continue  # binary artifact can't be processed
                    raise ValueError("Unexpected lack of artifactLocation tag")
                path: str = artifact_data.get('uri', '').replace('file://', '')
                region_data = location_data.get('region')
                if not region_data:
                    continue  # TODO: cover this case as comment to the file as a whole
                line: str = region_data.get('startLine', '')
                result.append(utils.ReportData(
                    symbol="Reported issue",
                    message=f"{who} : {what}",
                    path=path,
                    line=int(line)
                ))
    return result


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter  # see https://github.com/PyCQA/pylint/issues/259
