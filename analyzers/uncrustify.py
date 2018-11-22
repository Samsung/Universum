#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import difflib
import sys
import os

import re
import sh

from . import utils


class UncrustifyAnalyzer(object):
    """
    Uncrustify runner.
    Specify parameters such as file list, config file for code report tool.
    For example: universum_uncrustify --files *.py tests/
    Output: json of the found issues in the code.
    """
    @staticmethod
    def define_arguments():
        parser = argparse.ArgumentParser(description="Uncrustify analyzer")
        parser.add_argument("--files", "-f", dest="file_names", nargs="*", default=[],
                            help="File or directory to check; accepts multiple values; "
                                 "all files specified by both '--files' and '--file-list' "
                                 "are gathered into one combined list of files")
        parser.add_argument("--file-list", "-fl", dest="file_lists", nargs="*", default=[],
                            help="Text file with list of files or directories to check; "
                                 "can be used with '--files'; accepts multiple values; "
                                 "all files specified by both '--files' and '--file-list' "
                                 "are gathered into one combined list of files")
        parser.add_argument("--cfg-file", "-cf", dest="cfg_file",
                            help="Name of the configuration file of Uncrustify; "
                                 "can also be set via 'UNCRUSTIFY_CONFIG' env. variable")
        parser.add_argument("--filter-regex", "-r", dest="pattern_form", nargs="*", default=[],
                            help="(optional) Regular expression filter to apply to "
                                 "combined list of files to check")

        utils.add_common_arguments(parser)
        return parser

    @staticmethod
    def add_files_recursively(item_path):
        files = []
        item_path = os.path.join(os.getcwd(), item_path)
        if os.path.isfile(item_path):
            files.append(item_path)
        elif os.path.isdir(item_path):
            for root_dir, _, files_name in os.walk(item_path):
                for file_name in files_name:
                    files.append(os.path.join(root_dir, file_name))
        else:
            sys.stderr.write(item_path + " doesn't exist.")
            return 2

        return files

    def __init__(self, settings):
        self.settings = settings

    def parse_files(self):
        files = []
        file_lines = []
        for file_name in self.settings.file_names:
            files.extend(self.add_files_recursively(file_name))
        for file_list in self.settings.file_lists:
            with open(file_list) as f:
                for file_name in f.readlines():
                    file_lines.append(file_name.strip())
        for file_name in file_lines:
            files.extend(self.add_files_recursively(file_name))


        for pattern in self.settings.pattern_form:
            regexp = re.compile(pattern)
            files = [file_name for file_name in files if regexp.match(file_name)]

        return files

    def execute(self):  # pylint: disable=too-many-locals

        if not self.settings.cfg_file and ('UNCRUSTIFY_CONFIG' not in os.environ):
            sys.stderr.write("Please specify the '--cfg_file' parameter "
                             "or set an env. variable 'UNCRUSTIFY_CONFIG'")
            return 2

        analyze_files = self.parse_files()
        if not analyze_files:
            sys.stderr.write("Please provide at least one file for analysis")
            return 2
        uncrustify_folder = os.path.join(os.getcwd(), "uncrustify")
        try:
            cmd = sh.Command("uncrustify")
            cmd("-c", self.settings.cfg_file, "--prefix", uncrustify_folder, analyze_files)
        except sh.ErrorReturnCode as e:
            sys.stderr.write(str(e)+"\n")
        issues_loads = []
        for file_name in analyze_files:
            with open(file_name) as f1:
                f1_text = f1.read()
            with open(uncrustify_folder+'/'+file_name) as f2:
                f2_text = f2.read()
            f1_lines = f1_text.splitlines(1)
            f2_lines = f2_text.splitlines(1)
            # generate html diff ----------------------------------------------
            differ = difflib.HtmlDiff(tabsize=8, wrapcolumn=82)
            html = differ.make_file(f1_lines, f2_lines, context=False)
            with open('uncrustify/' + file_name + '.html', 'w') as outfile:
                outfile.write(html)

            file_sequence = difflib.SequenceMatcher(a=f1_lines, b=f2_lines)
            # Get matching in lines
            matching_blocks = file_sequence.get_matching_blocks()
            prev_match = matching_blocks[0]
            for match in matching_blocks[1:]:
                if prev_match.a + prev_match.size != match.a:
                    # Collect difference line in block
                    block_before = f1_lines[(prev_match.a + prev_match.size - 1):(match.a)]
                    block_after = f2_lines[(prev_match.b + prev_match.size - 1):(match.b)]
                    before_str = ''.join(block_before)
                    after_str = ''.join(block_after)
                    # Replace whitespaces tabs newlines symbols
                    for old_str, new_str in zip([u" ", u"\t", u"\n"],
                                                [u"\u00b7", u"\u2192\u2192\u2192\u2192", u"\u2193\u000a"]):
                        before_str = before_str.replace(old_str, new_str)
                        after_str = after_str.replace(old_str, new_str)

                    issue = dict()
                    issue["symbol"] = "Uncrustify Code Style issue"
                    # Check block size
                    if len(block_before) > 11:
                        issue["message"] = "\nLagre block of code ("+ str(len(block_before)) +" lines) have issues\n"
                    else:
                        # message with before&after
                        issue["message"] = "\nOriginal code:\n```diff\n" + before_str + "```\n" + \
                                           "Uncrustify generated code:\n```diff\n" + after_str + \
                                           "```\n"

                    issue["path"] = os.path.relpath(file_name, os.getcwd())
                    issue["line"] = match.a
                    issues_loads.append(issue)
                    prev_match = match
            utils.analyzers_output(self.settings.result_file, issues_loads)
            return 1
        return 0


def form_arguments_for_documentation():
    return UncrustifyAnalyzer.define_arguments()


def main():
    analyzer_namespace = UncrustifyAnalyzer.define_arguments().parse_args()
    analyze = UncrustifyAnalyzer(analyzer_namespace)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
