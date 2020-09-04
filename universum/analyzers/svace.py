import argparse
import os
import sys

import sh
from lxml import etree

from . import utils


class SvaceAnalyzer:

    @staticmethod
    def define_arguments():
        parser = argparse.ArgumentParser(description="Svace analyzer")
        parser.add_argument("--build-cmd", dest="build_cmd", nargs='+',
                            help="Relative path to build script or command itself")
        parser.add_argument("--lang", dest="lang", choices=["JAVA", "CXX"], help="Language to analyze")
        parser.add_argument("--project-name", dest="project_name", help="Svace project name defined on server")
        utils.add_common_arguments(parser)
        return parser

    def __init__(self, settings):
        self.settings = settings

        self.settings.svace_home = "/opt/svace-x64-linux"
        self.project_name = self.settings.project_name + "_" + self.settings.lang

        self.work_folder = os.path.join(os.getcwd(), self.project_name)
        self.settings.jack_option = "--enable-jack-interception"
        self.settings.hash_server_memory = "2048"
        self.settings.verbose = "--verbose"

        if self.settings.lang.upper() == "JAVA":
            self.disabled_language = "cxx"
            self.enabled_language = "java"
        elif self.settings.lang.upper() == "CXX":
            self.disabled_language = "java"
            self.enabled_language = "cxx"
        self.json_file = settings.result_file

    def analyze(self):
        try:
            cmd_analyze = sh.Command(self.settings.svace_home + "/bin/svace")
            cmd_analyze("analyze", "-q", "--svace-dir", self.work_folder, "--disable-language",
                        self.disabled_language, "--enable-language", self.enabled_language,
                        "--preset", self.enabled_language)

            svres_full = os.path.join(self.work_folder, "analyze-res", self.project_name + ".svres")
            root = etree.parse(svres_full)

            warn_info = root.xpath('//WarnInfo')
            issues_loads = []
            for info in warn_info:
                issue = dict()
                issue["symbol"] = info.attrib["warnClass"]
                issue["message"] = "\nWarning message: " + info.attrib["msg"]
                issue["path"] = info.attrib["file"]
                issue["line"] = info.attrib["line"]
                issues_loads.append(issue)
            utils.analyzers_output(self.json_file, issues_loads)
            if issues_loads:
                return 1
        except etree.XMLSyntaxError as e:
            sys.stderr.write(e.error_log) #TODO: check is it corerct
            return 2
        except Exception as e:
            sys.stderr.write(str(e))
            return 2
        return 0

    def execute(self):
        if not os.path.exists(self.settings.svace_home):
            sys.stderr.write("SVACE_HOME=" + self.settings.svace_home + " folder doesn't exist.")
            return 2

        try:
            cmd_init = sh.Command(self.settings.svace_home + "/bin/svace")
            cmd_init("init", "-f", "--shared=all", "--bare", self.work_folder)
            cmd_build = sh.Command(self.settings.svace_home + "/bin/svace")
            cmd_build("build", self.settings.jack_option, self.settings.verbose,
                      "--hash-server-memory", self.settings.hash_server_memory,
                      "--svace-dir", self.work_folder, self.settings.build_cmd,
                      _err=sys.stderr, _out=sys.stdout)
        except sh.ErrorReturnCode_255:
            sys.stderr.write("Svace exited with error code 255. No build object found.\n")
            return 2
        except Exception as e:
            sys.stderr.write(str(e))
            return 2
        return self.analyze()


def form_arguments_for_documentation():
    return SvaceAnalyzer.define_arguments()


def main():
    analyzer_namespace = SvaceAnalyzer.define_arguments().parse_args()
    analyze = SvaceAnalyzer(analyzer_namespace)
    return analyze.execute()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
