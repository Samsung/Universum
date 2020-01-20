#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import argparse
import glob
import json
import sys

import sh

from analyzers import utils


class PylintAnalyzer:
    """
    Pylint runner.
    Specify parameters such as project folders, config file for code report tool.
    For example:
    universum_pylint --python-version 2 --files *.py tests/
    ./pylint.py --python-version 2 --files *.py tests/
    Output: json of the found issues in the code.
    """

    @staticmethod
    def define_arguments():
        parser = argparse.ArgumentParser(description="Pylint analyzer")
        parser.add_argument("--files", dest="file_list", nargs='+', help="Python files and Python packages for Pylint.")
        parser.add_argument("--rcfile", dest="rcfile", help="Specify a configuration file.")
        parser.add_argument("--python-version", dest="version", default="3", choices=["2", "3"],
                            help="Version of Python")
        utils.add_common_arguments(parser)
        return parser

    def __init__(self, settings):
        self.settings = settings
        self.json_file = settings.result_file

    def execute(self):
        if not self.settings.file_list:
            sys.stderr.write("Please, specify [--files] option. Files could be defined as a single python file,"
                             " *.py or directories with __init__.py file in the directory.\n")
            return 2

        issues = []
        files = []
        if not self.settings.rcfile:
            self.settings.rcfile = ""

        for pattern in self.settings.file_list:
            files.extend(glob.glob(pattern))
        try:
            if self.settings.version == "3":
                cmd = sh.Command("python3")
            else:
                cmd = sh.Command("python2")
            issues = cmd("-m", "pylint", "-f", "json", "--rcfile=" + self.settings.rcfile, *files).stdout
        except sh.CommandNotFound as e:
            sys.stderr.write("No such file or command as '" + str(e) + "'. "
                             "Make sure, that required code report tool is installed.\n")
        except Exception as e:
            if e.stderr and not e.stdout:
                sys.stderr.write(e.stderr)
                return 2
            issues = e.stdout

        try:
            issues_loads = []
            loads = []
            if issues:
                loads = json.loads(issues)
            for issue in loads:
                # pylint has its own escape rules for json output of "message" values.
                # it uses cgi.escape lib and escapes symbols <>&
                issue["message"] = issue["message"].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                issues_loads.append(issue)
            utils.analyzers_output(self.json_file, issues_loads)
            if issues_loads:
                return 1
        except ValueError as e:
            sys.stderr.write(e.message)
            sys.stderr.write("The following string produced by the pylint launch cannot be parsed as JSON:\n")
            sys.stderr.write(issues)
            return 2
        return 0


def form_arguments_for_documentation():
    return PylintAnalyzer.define_arguments()


def main():
    analyzer_namespace = PylintAnalyzer.define_arguments().parse_args()
    analyze = PylintAnalyzer(analyzer_namespace)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
