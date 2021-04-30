import argparse
import sys

from typing import List

from . import utils


def form_arguments_for_documentation() -> argparse.ArgumentParser:
    return _mypy_argument_parser()


def main() -> int:
    settings = _mypy_argument_parser().parse_args()

    cmd = [f"python{settings.version}", '-m', 'mypy', '--ignore-missing-imports']
    if settings.config_file:
        cmd.append(f'--config-file={settings.config_file}')
    cmd.extend(utils.expand_files_argument(settings))

    return utils.report_parsed_outcome(cmd, _mypy_output_parser, settings.result_file)


def _mypy_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pylint analyzer")
    utils.add_files_argument(parser)
    parser.add_argument("--config-file", dest="config_file", type=str, help="Specify a configuration file.")
    utils.add_python_version_argument(parser)
    utils.add_result_file_argument(parser)
    return parser


def _mypy_output_parser(output: str) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for raw_line in output.split('\n')[:-2]:  # last line is summary
        data: List[str] = raw_line.split(':', 2)
        if len(data) != 3:
            raise ValueError("Wrong format of output analyzer data: " + raw_line)
        result.append(utils.ReportData(
            symbol="Mypy type annotation issue",
            message=data[2],
            path=data[0],
            line=int(data[1])
        ))
    return result


if __name__ == "__main__":
    sys.exit(main())
