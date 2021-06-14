import argparse
import difflib
import os
import shutil
from pathlib import Path

from typing import Callable, List, Optional, Tuple

from . import utils


def uncrustify_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Uncrustify analyzer")
    parser.add_argument("--cfg-file", "-cf", dest="cfg_file",
                        help="Name of the configuration file of Uncrustify; "
                             "can also be set via 'UNCRUSTIFY_CONFIG' env. variable")
    parser.add_argument("--output-directory", "-od", dest="output_directory", default="uncrustify",
                        help="Directory to store fixed files, generated by Uncrustify "
                             "and HTML files with diff; the default value is 'uncrustify'"
                             "Has to be distinct from source directory")
    parser.add_argument("--report-html", dest="write_html", action="store_true", default=False,
                        help="(optional) Set to generate html reports for each modified file")
    return parser


@utils.sys_exit
@utils.analyzer(uncrustify_argument_parser())
def main(settings: argparse.Namespace) -> List[utils.ReportData]:
    if not shutil.which('uncrustify'):
        raise EnvironmentError("Please install uncrustify")
    if not settings.cfg_file and 'UNCRUSTIFY_CONFIG' not in os.environ:
        raise EnvironmentError("Please specify the '--cfg_file' parameter "
                               "or set an env. variable 'UNCRUSTIFY_CONFIG'")
    target_folder: Path = utils.normalize(settings.output_directory)
    if target_folder.exists() and target_folder.samefile(Path.cwd()):
        raise EnvironmentError("Target and source folders for uncrustify are not allowed to match")
    html_diff_file_writer: Optional[Callable[[Path, List[str], List[str]], None]] = None
    if settings.write_html:
        wrapcolumn, tabsize = _get_wrapcolumn_tabsize(settings.cfg_file)
        html_diff_file_writer = HtmlDiffFileWriter(target_folder, wrapcolumn, tabsize)

    files: List[Tuple[Path, Path]] = []
    for src_file in settings.file_list:
        src_file_absolute = utils.normalize(src_file)
        src_file_relative = src_file_absolute.relative_to(Path.cwd())
        target_file_absolute: Path = target_folder.joinpath(src_file_relative)
        files.append((src_file_absolute, target_file_absolute))
    cmd = ["uncrustify", "-q", "-c", settings.cfg_file, "--prefix", settings.output_directory]
    cmd.extend(settings.file_list)
    utils.run_for_output(cmd)
    return uncrustify_output_parser(files, html_diff_file_writer)


class HtmlDiffFileWriter:

    def __init__(self, target_folder: Path, wrapcolumn: int, tabsize: int) -> None:
        self.target_folder = target_folder
        self.differ = difflib.HtmlDiff(tabsize=tabsize, wrapcolumn=wrapcolumn)

    def __call__(self, file: Path, src: List[str], target: List[str]) -> None:
        file_relative = file.relative_to(Path.cwd())
        out_file_name: str = str(file_relative).replace('/', '_') + '.html'
        with open(self.target_folder.joinpath(out_file_name), 'w') as out_file:
            out_file.write(self.differ.make_file(src, target, context=False))


def uncrustify_output_parser(files: List[Tuple[Path, Path]],
                             write_diff_file: Optional[Callable[[Path, List[str], List[str]], None]]
                             ) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for src_file, uncrustify_file in files:
        with open(src_file) as src:
            src_lines = src.readlines()
        with open(uncrustify_file) as fixed:
            fixed_lines = fixed.readlines()

        issues = _get_issues_from_diff(src_file, src_lines, fixed_lines)
        if issues and write_diff_file:
            write_diff_file(src_file, src_lines, fixed_lines)
        result.extend(issues)
    return result


def _get_wrapcolumn_tabsize(cfg_file: str) -> Tuple[int, int]:
    with open(cfg_file) as config:
        for line in config.readlines():
            if line.startswith("code_width"):
                wrapcolumn = int(line.split()[2])
            if line.startswith("input_tab_size"):
                tabsize = int(line.split()[2])
    return wrapcolumn, tabsize


def _get_issues_from_diff(src_file: Path, src: List[str], target: List[str]) -> List[utils.ReportData]:
    result = []
    matching_blocks: List[difflib.Match] = \
        difflib.SequenceMatcher(a=src, b=target).get_matching_blocks()
    previous_match = matching_blocks[0]
    for match in matching_blocks[1:]:
        block = _get_mismatching_block(previous_match, match, src, target)
        previous_match = match
        if not block:
            continue
        line, before, after = block
        path: Path = src_file.relative_to(Path.cwd())
        message = _get_issue_message(before, after)
        result.append(utils.ReportData(
            symbol="Uncrustify Code Style issue",
            message=message,
            path=str(path),
            line=line
        ))

    return result


def _get_issue_message(before: str, after: str) -> str:
    # The maximum number of lines to write separate comments for
    # If exceeded, summarized comment will be provided instead
    max_lines = 11
    diff_size = len(before.splitlines())
    if diff_size > max_lines:
        message = f"\nLarge block of code ({diff_size} lines) has issues\n" + \
                  f"Non-compliant code blocks exceeding {max_lines} lines are not reported\n"
    else:
        # Message with before&after
        message = f"\nOriginal code:\n```diff\n{before}```\n" + \
                  f"Uncrustify generated code:\n```diff\n{after}```\n"
    return message


def _get_mismatching_block(previous_match: difflib.Match,  # src[a:a+size] = target[b:b+size]
                           match: difflib.Match,
                           src: List[str], target: List[str]
                           ) -> Optional[Tuple[int, str, str]]:
    previous_match_end_in_src = previous_match.a + previous_match.size
    previous_match_end_in_target = previous_match.b + previous_match.size
    match_start_in_src = match.a
    match_start_in_target = match.b
    if previous_match_end_in_src == match_start_in_src:
        return None
    line = match_start_in_src
    before = _get_text_for_block(previous_match_end_in_src - 1, match_start_in_src, src)
    after = _get_text_for_block(previous_match_end_in_target - 1, match_start_in_target, target)
    return line, before, after


def _get_text_for_block(start: int, end: int, lines: List[str]) -> str:
    return _replace_invisible_symbols(''.join(lines[start: end]))


def _replace_invisible_symbols(line: str) -> str:
    for old_str, new_str in zip([u" ", u"\t", u"\n"], [u"\u00b7", u"\u2192\u2192\u2192\u2192", u"\u2193\u000a"]):
        line = line.replace(old_str, new_str)
    return line


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter  # see https://github.com/PyCQA/pylint/issues/259
