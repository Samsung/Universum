import argparse
import difflib
import pathlib
import shutil
from typing import Callable, List, Optional, Tuple

from . import utils


class HtmlDiffFileWriter:

    def __init__(self, target_folder: pathlib.Path, wrapcolumn: int, tabsize: int) -> None:
        self.target_folder = target_folder
        self.differ = difflib.HtmlDiff(tabsize=tabsize, wrapcolumn=wrapcolumn)

    def __call__(self, file: pathlib.Path, src: List[str], target: List[str]) -> None:
        file_relative = file.relative_to(pathlib.Path.cwd())
        out_file_name: str = str(file_relative).replace('/', '_') + '.html'
        with open(self.target_folder.joinpath(out_file_name), 'w', encoding="utf-8") as out_file:
            out_file.write(self.differ.make_file(src, target, context=False))


DiffWriter = Callable[[pathlib.Path, List[str], List[str]], None]


def diff_analyzer_output_parser(files: List[Tuple[pathlib.Path, pathlib.Path]],
                                write_diff_file: Optional[DiffWriter]
                                ) -> List[utils.ReportData]:
    result: List[utils.ReportData] = []
    for src_file, dst_file in files:
        with open(src_file, encoding="utf-8") as src:
            src_lines = src.readlines()
        with open(dst_file, encoding="utf-8") as fixed:
            fixed_lines = fixed.readlines()

        issues = _get_issues_from_diff(src_file, src_lines, fixed_lines)
        if issues and write_diff_file:
            write_diff_file(src_file, src_lines, fixed_lines)
        result.extend(issues)
    return result


def _get_issues_from_diff(src_file: pathlib.Path, src: List[str], target: List[str]) -> List[utils.ReportData]:
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
        path: pathlib.Path = src_file.relative_to(pathlib.Path.cwd())
        message = _get_issue_message(before, after)
        result.append(utils.ReportData(
            symbol="Code Style issue",
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
                  f"Fixed code:\n```diff\n{after}```\n"
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
    return _replace_whitespace_characters(''.join(lines[start: end]))


_whitespace_character_mapping = {
    " ": "\u00b7",
    "\t": "\u2192\u2192\u2192\u2192",
    "\n": "\u2193\u000a"
}.items()


def _replace_whitespace_characters(line: str) -> str:
    for old_str, new_str in _whitespace_character_mapping:
        line = line.replace(old_str, new_str)
    return line


def diff_analyzer_argument_parser(description: str, module_path: str, output_directory: str) -> argparse.ArgumentParser:
    parser = utils.create_parser(description, module_path)
    parser.add_argument("--output-directory", "-od", dest="output_directory", default=output_directory,
                        help=f"Directory to store fixed files and HTML files with diff; the default "
                             f"value is '{output_directory}'. Has to be distinct from source directory")
    parser.add_argument("--report-html", dest="write_html", action="store_true", default=False,
                        help="(optional) Set to generate html reports for each modified file")
    return parser


def diff_analyzer_common_main(settings: argparse.Namespace) -> None:
    settings.target_folder = utils.normalize_path(settings.output_directory)
    if settings.target_folder.exists() and settings.target_folder.samefile(pathlib.Path.cwd()):
        raise EnvironmentError("Target folder must not be identical to source folder")

    settings.target_folder.mkdir(parents=True, exist_ok=True)

    if not shutil.which(settings.executable):
        raise EnvironmentError(f"{settings.name} executable '{settings.executable}' is not found. "
                               f"Please install {settings.name} or fix the executable name.")
