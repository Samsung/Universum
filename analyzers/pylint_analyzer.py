# -*- coding: UTF-8 -*-

import glob
import json
import sys
import sh

__all__ = ["PylintAnalyzer"]


class PylintAnalyzer(object):
    """
    Pylint runner.
    Specify parameters such as type, project folders, config file for code report tool.
    For example: ./code_report.py --type=pylint --files *.py tests/
    Output: json of the found issues in the code.
    """
    @staticmethod
    def define_arguments(parser, args):
        parser.add_argument("--files", dest="file_list", nargs='+', help="Python files and Python packages for Pylint.")
        parser.add_argument("--rcfile", dest="rcfile", help="Specify a configuration file.")
        return parser.parse_args(args)

    def __init__(self, settings, static_analyzer):
        self.settings = settings
        self.settings.static_analyzer = static_analyzer

    def execute(self):
        if not self.settings.file_list:
            sys.stderr.write("Please, specify [--files] option. Files could be defined as a single python file,"
                             " *.py or directories with __init__.py file in the directory.")
            return 1

        issues = []
        files = []
        if not self.settings.rcfile:
            self.settings.rcfile = ""

        for pattern in self.settings.file_list:
            files.extend(glob.glob(pattern))
        try:
            if self.settings.static_analyzer == "pylint3":
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
