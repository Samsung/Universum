#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import argparse
import json
import glob
import sh
from _universum.utils import format_traceback


class CodeReport(object):
    """
    Code report module for project.
    Specify parameters such as type, project folders, config file for code report tool.
    For example: ./code_report.py --type=pylint --files *.py tests/
    Output: json of the found issues in the code.
    """
    description = "Code report module of Universum "

    @staticmethod
    def define_arguments(parser):
        parser.add_argument("--type", dest="code_report", choices=["pylint", "pylint3"],
                            help="Define, which code report tool should be used.")
        parser.add_argument("--files", dest="file_list", nargs='+', help="Files for code report.")
        parser.add_argument("--rcfile", dest="rcfile", help="Specify a configuration file.")

    def __init__(self, settings):
        super(CodeReport, self).__init__()
        self.settings = settings

    def run_pylint(self):
        issues = []
        files = []
        if not self.settings.rcfile:
            self.settings.rcfile = ""

        for pattern in self.settings.file_list:
            files.extend(glob.glob(pattern))
        try:
            if self.settings.code_report == "pylint3":
                cmd = sh.Command("python3")
            else:
                cmd = sh.Command("python")
            issues = cmd("-m", "pylint", "-f", "json", "--rcfile=" + self.settings.rcfile, *files).stdout
        except sh.CommandNotFound as e:
            sys.stderr.write("No such file or command as '" + str(e) + "'. "
                             "Make sure, that required code report tool is installed.\n")
        except Exception as e:
            if e.stderr and not e.stdout:
                sys.stderr.write(e.stderr)
                return 1
            elif e.stdout:
                issues = e.stdout

        if issues:
            try:
                issues_loads = []
                loads = json.loads(issues)
                for issue in loads:
                    # pylint has its own escape rules for json output of "message" values.
                    # it uses cgi.escape lib and escapes symbols <>&
                    issue["message"] = issue["message"].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                    issues_loads.append(issue)
                sys.stdout.write(json.dumps(issues_loads))
            except ValueError as e:
                sys.stderr.write(e.message)
                sys.stderr.write("The following string produced by the pylint launch cannot be parsed as JSON:\n")
                sys.stderr.write(issues)
        return 0

    def execute(self):
        if self.settings.code_report in ["pylint", "pylint3"]:
            return self.run_pylint()
        return 2


def main():
    parser = argparse.ArgumentParser()
    CodeReport.define_arguments(parser)
    settings = parser.parse_args()
    report = CodeReport(settings)
    return report.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
