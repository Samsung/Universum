import argparse
import json

from typing import List

from . import utils


def pylint_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pylint analyzer")
    parser.add_argument("--rcfile", dest="rcfile", type=str, help="Specify a configuration file.")
    utils.add_python_version_argument(parser)
    return parser


@utils.sys_exit
@utils.analyzer(pylint_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    cmd = [f"python{settings.version}", '-m', 'pylint', '-f', 'json']
    if settings.rcfile:
        cmd.append(f'--rcfile={settings.rcfile}')
    cmd.extend(settings.file_list)
    output, _ = utils.run_for_output(cmd)
    return pylint_output_parser(output)


def pylint_output_parser(output: str) -> List[utils.ReportData]:
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
    main()  # pylint: disable=no-value-for-parameter  # see https://github.com/PyCQA/pylint/issues/259
