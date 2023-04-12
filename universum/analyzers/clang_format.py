import argparse
import pathlib
from typing import Callable, List, Optional, Tuple

import yaml

from . import utils, diff_utils


def clang_format_argument_parser() -> argparse.ArgumentParser:
    parser = diff_utils.diff_analyzer_argument_parser("Clang-format analyzer", __file__, "clang-format")
    parser.add_argument("--executable", "-e", dest="executable", default="clang-format",
                        help="The name of the clang-format executable, default: clang-format")
    parser.add_argument("--style", dest="style",
                        help="The 'style' parameter of the clang-format. Can be literal 'file' string or "
                             "path to real file. See the clang-format documentation for details.")
    return parser


def _add_style_param_if_present(cmd: List[str], settings: argparse.Namespace) -> None:
    if settings.style:
        cmd.extend(["-style", settings.style])


@utils.sys_exit
@utils.analyzer(clang_format_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    settings.name = "clang-format"
    diff_utils.diff_analyzer_common_main(settings)

    html_diff_file_writer: Optional[Callable[[pathlib.Path, List[str], List[str]], None]] = None
    if settings.write_html:
        wrapcolumn, tabsize = _get_wrapcolumn_tabsize(settings)
        html_diff_file_writer = diff_utils.HtmlDiffFileWriter(settings.target_folder, wrapcolumn, tabsize)

    files: List[Tuple[pathlib.Path, pathlib.Path]] = []
    for src_file_absolute, target_file_absolute, _ in utils.get_files_with_absolute_paths(settings):
        files.append((src_file_absolute, target_file_absolute))
        cmd = [settings.executable, src_file_absolute]
        _add_style_param_if_present(cmd, settings)
        output, _ = utils.run_for_output(cmd)
        with open(target_file_absolute, "w", encoding="utf-8") as output_file:
            output_file.write(output)

    return diff_utils.diff_analyzer_output_parser(files, html_diff_file_writer)


def _get_wrapcolumn_tabsize(settings: argparse.Namespace) -> Tuple[int, int]:
    cmd = [settings.executable, "--dump-config"]
    _add_style_param_if_present(cmd, settings)
    output, error = utils.run_for_output(cmd)
    if error:
        raise utils.AnalyzerException(message="clang-format --dump-config failed with the following error output: " +
                                              error)
    try:
        clang_style = yaml.safe_load(output)
        return clang_style["ColumnLimit"], clang_style["IndentWidth"]
    except yaml.YAMLError as parse_error:
        raise utils.AnalyzerException(message="Parsing of clang-format config produced the following error: " +
                                              str(parse_error))
    except KeyError as key_error:
        raise utils.AnalyzerException(message="Cannot find key in yaml during parsing of clang-format config: " +
                                              str(key_error))


if __name__ == "__main__":
    main()
