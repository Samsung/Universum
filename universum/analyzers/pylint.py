import argparse
import glob
import json
import sys
import subprocess

from . import utils


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
        parser.add_argument("--files", dest="file_list", nargs='+', required=True,
                            help="Python files and Python packages for Pylint. "
                                 "Files could be defined as a single python file"
                                 " *.py or directories with __init__.py file in the directory.")
        parser.add_argument("--rcfile", dest="rcfile", type=str, help="Specify a configuration file.")
        parser.add_argument("--python-version", dest="version", default="3",
                            help="Version of the python interpreter, such as 2, 3 or 3.7. "
                                 "Pylint analyzer uses this parameter to select python binary for launching pylint. "
                                 "For example, if the version is 3.7, it uses the following command: "
                                 "'python3.7 -m pylint <...>'")
        utils.add_common_arguments(parser)
        return parser

    def __init__(self, settings):
        self.settings = settings

    def execute(self):
        cmd = [f"python{self.settings.version}", '-m', 'pylint', '-f', 'json']
        if self.settings.rcfile:
            cmd.append(f'--rcfile={self.settings.rcfile}')

        for pattern in self.settings.file_list:
            cmd.extend(glob.glob(pattern))

        result = subprocess.run(cmd, universal_newlines=True,  # pylint: disable=subprocess-run-check
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.stderr and not result.stdout:
            sys.stderr.write(result.stderr)
            return result.returncode

        return self._handle_pylint_output(result.stdout)

    def _handle_pylint_output(self, issues: str) -> int:
        try:
            loads = json.loads(issues)
            issues_loads = []
            for issue in loads:
                # pylint has its own escape rules for json output of "message" values.
                # it uses cgi.escape lib and escapes symbols <>&
                issue["message"] = issue["message"].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                issues_loads.append(issue)

            utils.analyzers_output(self.settings.result_file, issues_loads)
            if issues_loads:
                return 1
            return 0

        except ValueError as e:
            sys.stderr.write(str(e))
            sys.stderr.write("The following string produced by the pylint launch cannot be parsed as JSON:\n")
            sys.stderr.write(issues)
            return 2


def form_arguments_for_documentation():
    return PylintAnalyzer.define_arguments()


def main():
    analyzer_namespace = PylintAnalyzer.define_arguments().parse_args()
    analyze = PylintAnalyzer(analyzer_namespace)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
