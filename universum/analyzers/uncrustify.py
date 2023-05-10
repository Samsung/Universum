import argparse
import os
import pathlib
import re
from typing import Callable, List, Optional, Tuple

from . import utils, diff_utils


def uncrustify_argument_parser() -> argparse.ArgumentParser:
    parser = diff_utils.diff_analyzer_argument_parser("Uncrustify analyzer", __file__, "uncrustify")
    parser.add_argument("--cfg-file", "-cf", dest="cfg_file",
                        help="Name of the configuration file of Uncrustify; "
                             "can also be set via 'UNCRUSTIFY_CONFIG' env. variable")
    return parser


@utils.sys_exit
@utils.analyzer(uncrustify_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    settings.name = "uncrustify"
    settings.executable = "uncrustify"
    diff_utils.diff_analyzer_common_main(settings)

    if not settings.cfg_file and 'UNCRUSTIFY_CONFIG' not in os.environ:
        raise EnvironmentError("Please specify the '--cfg-file' parameter "
                               "or set 'UNCRUSTIFY_CONFIG' environment variable")

    html_diff_file_writer: Optional[Callable[[pathlib.Path, List[str], List[str]], None]] = None
    if settings.write_html:
        wrapcolumn, tabsize = _get_wrapcolumn_tabsize(settings.cfg_file)
        html_diff_file_writer = diff_utils.HtmlDiffFileWriter(settings.target_folder, wrapcolumn, tabsize)

    cmd = ["uncrustify", "-q", "-c", settings.cfg_file, "--prefix", settings.output_directory]
    files: List[Tuple[pathlib.Path, pathlib.Path]] = []
    for src_file_absolute, target_file_absolute, src_file_relative in utils.get_files_with_absolute_paths(settings):
        files.append((src_file_absolute, target_file_absolute))
        cmd.append(src_file_relative)

    utils.run_for_output(cmd)
    return diff_utils.diff_analyzer_output_parser(files, html_diff_file_writer)


def _get_wrapcolumn_tabsize(cfg_file: str) -> Tuple[int, int]:
    wrapcolumn = 120
    tabsize = 4
    with open(cfg_file, encoding="utf-8") as config:
        for line in config.readlines():
            match = re.match(r"^\s*([A-Za-z_]+)\s*[,\=]?\s*([0-9]+)\s*$", line)
            if not match:
                continue
            groups = match.groups()
            if groups[0] == "code_width":
                wrapcolumn = int(groups[1])
            if groups[0] == "input_tab_size":
                tabsize = int(groups[1])
    return wrapcolumn, tabsize


if __name__ == "__main__":
    main()
