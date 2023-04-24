import argparse
from typing import List

from . import utils


def mypy_argument_parser() -> argparse.ArgumentParser:
    parser = utils.create_parser("Mypy analyzer", __file__)
    parser.add_argument("--config-file", dest="config_file", type=str, help="Specify a configuration file.")
    utils.add_python_version_argument(parser)
    return parser


@utils.sys_exit
@utils.analyzer(mypy_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    cmd = [f"python{settings.version}", '-m', 'mypy']
    if settings.config_file:
        cmd.append(f'--config-file={settings.config_file}')
    cmd.extend(settings.file_list)
    output, _ = utils.run_for_output(cmd)
    return mypy_output_parser(output)


def mypy_output_parser(output: str) -> List[utils.ReportData]:
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
    main()  # pylint: disable=no-value-for-parameter  # see https://github.com/PyCQA/pylint/issues/259
