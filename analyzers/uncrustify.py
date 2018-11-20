#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import difflib
import sys
import os

import glob2
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
        parser.add_argument("--file-names", "-fn", dest="file_names", nargs="+",
                            help="Expression '*.c', '*.cpp', '*.h', '*.java' "
                                 "or C/C++/C header/java files for analyser")
        parser.add_argument("--file-lists", "-fl", dest="file_lists", nargs="+",
                            help="File with list of file for analyser")
        parser.add_argument("--cfg-file", "-cf", dest="cfg_file", nargs=1,
                            help="Specify a configuration file or UNCRUSTIFY_CONFIG")
        parser.add_argument("--pattern-form", "-pf", dest="pattern_form", nargs="+",
                            help="Specify pattern which apply "
                                 "to the total file list from [--file_names] and [--file_list]")

        utils.add_common_arguments(parser)
        return parser

    @staticmethod
    def add_files_recursively(item_path):
        files = []
        if os.path.isfile(item_path):
            files.append(item_path)
        elif os.path.isdir(item_path):
            folder_path = os.path.join(os.getcwd(), item_path)
            for root_dir, _, files_name in os.walk(folder_path):
                for file_name in files_name:
                    files.append(os.path.join(root_dir, file_name))
        else:
            sys.stderr.write(item_path + " doesn't exist.")
            return 2

        return files

    def parse_files(self):
        files = []
        filter_files = []
        if self.file_names:
            for file_name in self.file_names:
                files.extend(self.add_files_recursively(file_name))
        if self.file_lists:
            file_lines = []
            for file_list in self.file_lists:
                with open(file_list) as f:
                    for file_name in f.readlines():
                        file_lines.append(file_name.strip())
            for file_name in file_lines:
                files.extend(self.add_files_recursively(file_name))
        if self.pattern_form:
            for pattern in self.pattern_form:
                for file_name in files:
                    if pattern not in file_name:
                        filter_files.append(file_name)
        else:
            filter_files = files
        return filter_files

    def __init__(self, settings):
        self.settings = settings
        self.cfg_file = settings.cfg_file
        self.file_names = settings.file_names
        self.file_lists = settings.file_lists
        self.pattern_form = settings.pattern_form
        self.json_file = settings.result_file

    def execute(self):  # pylint: disable=too-many-locals

        if not (self.file_names or self.file_lists):
            sys.stderr.write("Please, specify at least one option [--file_names] or [--file_list].")
            return 2
        if not self.cfg_file:
            sys.stderr.write("Please, specify [--cfg_file] option.")
            return 2

        analyze_files = self.parse_files()
        if not analyze_files:
            sys.stderr.write("Correct your parameters. List of files for uncrustify is empty.")
            return 2
        uncrustify_folder = os.path.join(os.getcwd(), "uncrustify")
        try:
            cmd = sh.Command("uncrustify")
            cmd("-c", self.cfg_file, "--prefix", uncrustify_folder, analyze_files)
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
            utils.analyzers_output(self.json_file, issues_loads)
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
