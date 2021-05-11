import argparse
import difflib
import sys
from os import environ
from pathlib import Path

import re
from typing import Callable, List, Optional, Tuple

from . import utils


def form_arguments_for_documentation() -> argparse.ArgumentParser:  # TODO: modify callers to remove wrapper
    return _uncrustify_argument_parser()


def main() -> int:
    settings: argparse.Namespace = _uncrustify_argument_parser().parse_args()
    target_folder: Path = Path.cwd().joinpath(settings.output_directory)
    if not settings.cfg_file and 'UNCRUSTIFY_CONFIG' not in environ:
        sys.stderr.write("Please specify the '--cfg_file' parameter "
                         "or set an env. variable 'UNCRUSTIFY_CONFIG'")
        return 2
    wrapcolumn, tabsize = _get_wrapcolumn_tabsize(settings.cfg_file)
    differ = difflib.HtmlDiff(tabsize=tabsize, wrapcolumn=wrapcolumn)

    def write_html_diff_file(file: Path, src: List[str], target: List[str]) -> None:
        # target_folder and differ used from outer scope
        file_relative = file.relative_to(Path.cwd())
        out_file_name: str = str(file_relative).replace('/', '_') + '.html'
        with open(target_folder.joinpath(out_file_name), 'w') as out_file:
            out_file.write(differ.make_file(src, target, context=False))

    files: List[Tuple[Path, Path]] = []
    try:
        src_files: List[Path] = _get_src_files(settings.file_list, settings.file_list_config)
        for pattern in settings.pattern_form:
            regexp = re.compile(pattern)  # TODO: combine patterns via join
            src_files = [file for file in src_files if regexp.match(str(file))]
        for src_file in src_files:
            src_file_relative = src_file.relative_to(Path.cwd())
            target_file: Path = target_folder.joinpath(src_file_relative)
            files.append((src_file, target_file))
        if not files:
            raise EnvironmentError("Please provide at least one file for analysis")
    except EnvironmentError as e:
        sys.stderr.write(str(e))
        return 2

    cmd = ["uncrustify", "-q", "-c", settings.cfg_file, "--prefix", settings.output_directory]
    cmd.extend([str(path.relative_to(Path.cwd())) for path in src_files])

    return utils.report_parsed_outcome(cmd,
                                       lambda _: _uncrustify_output_parser(files, write_html_diff_file),
                                       settings.result_file)


def _uncrustify_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Uncrustify analyzer")
    utils.add_files_argument(parser, False)
    parser.add_argument("--file-list", "-fl", dest="file_list_config", nargs="*", default=[],
                        help="Text file with list of files or directories to check; "
                             "can be used with '--files'; accepts multiple values; "
                             "all files specified by both '--files' and '--file-list' "
                             "are gathered into one combined list of files")
    parser.add_argument("--cfg-file", "-cf", dest="cfg_file",
                        help="Name of the configuration file of Uncrustify; "
                             "can also be set via 'UNCRUSTIFY_CONFIG' env. variable")
    parser.add_argument("--filter-regex", "-r", dest="pattern_form", nargs="*", default=[],
                        help="(optional) Python 2.7 regular expression filter to apply to "
                             "combined list of files to check")
    parser.add_argument("--output-directory", "-od", dest="output_directory", default="uncrustify",
                        help="Directory to store fixed files, generated by Uncrustify "
                             "and HTML files with diff; the default value is 'uncrustify'")
    utils.add_result_file_argument(parser)
    return parser


def _get_src_files(file_list: List[str], file_list_config: List[str]) -> List[Path]:
    files: List[Path] = []
    for file_list_stored in file_list_config:
        with open(file_list_stored) as f:
            for file_name in f.readlines():
                file_list.append(file_name.strip())
    for file_name in set(file_list):
        files.extend(_add_files_recursively(file_name))

    return files


def _add_files_recursively(item: str) -> List[Path]:
    files: List[Path] = []
    item_path = Path.cwd().joinpath(item)
    if item_path.is_file():
        files.append(item_path)
    elif item_path.is_dir():
        files.extend(item_path.joinpath(x) for x in item_path.rglob('*') if x.is_file())
    else:
        raise EnvironmentError(str(item_path) + " doesn't exist.")

    return files


def _uncrustify_output_parser(files: List[Tuple[Path, Path]],
                              write_diff_file: Callable[[Path, List[str], List[str]], None]
                              ) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for src_file, uncrustify_file in files:
        with open(src_file) as src:
            src_lines = src.readlines()
        with open(uncrustify_file) as fixed:
            fixed_lines = fixed.readlines()

        issues = _get_issues_from_diff(src_file, src_lines, fixed_lines)
        if issues:
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
    sys.exit(main())
