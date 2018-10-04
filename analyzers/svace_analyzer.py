# -*- coding: UTF-8 -*-

import json
import os
import sys
import sh
from lxml import etree

__all__ = ["SvaceAnalyzer"]


class SvaceAnalyzer(object):

    @staticmethod
    def define_arguments(parser, args):
        parser.add_argument("--build-cmd", dest="build_cmd", nargs='+',
                            help="Relative path to build script or command itself.")
        parser.add_argument("--lang", dest="lang", choices=["JAVA", "CXX"], help="Language to analyze.")
        return parser.parse_args(args)

    def __init__(self, settings, static_analyzer, json_file):
        self.settings = settings
        self.settings.static_analyzer = static_analyzer

        self.settings.svace_home = "/opt/svace-x64-linux"
        self.settings.product = "Svace_build_home"

        self.work_folder = os.path.join(os.getcwd(), self.settings.product)
        self.settings.jack_option = "--enable-jack-interception"
        self.settings.hash_server_memory = "2048"
        self.settings.verbose = "--verbose"

        if self.settings.lang.upper() == "JAVA":
            self.disabled_language = "cxx"
            self.enabled_language = "java"
        elif self.settings.lang.upper() == "CXX":
            self.disabled_language = "java"
            self.enabled_language = "cxx"

        self.json_file = json_file

    def analyze(self):
        try:
            cmd_analyze = sh.Command(self.settings.svace_home + "/bin/svace")
            run_analyze = cmd_analyze("analyze", "-q", "--svace-dir", self.work_folder, "--disable-language",
                                      self.disabled_language, "--enable-language", self.enabled_language,
                                      "--preset", self.enabled_language)

            svres_full = os.path.join(self.work_folder, "analyze-res", self.settings.product + ".svres")
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
            with open(self.json_file, "w") as outfile:
                outfile.write(json.dumps(issues_loads, indent=4))
            if issues_loads:
                return 1
        except etree.XMLSyntaxError as e:
            sys.stderr.write(e.error_log)
            return 2
        except Exception as e:
            sys.stderr.write(unicode(e))
            return 2
        return 0

    def execute(self):
        if not os.path.exists(self.settings.svace_home):
            sys.stderr.write("SVACE_HOME=" + self.settings.svace_home + " folder doesn't exist.")
            return 2

        try:
            cmd_init = sh.Command(self.settings.svace_home + "/bin/svace")
            run_init = cmd_init("init", "-f", "--shared=all", "--bare", self.work_folder)
            cmd_build = sh.Command(self.settings.svace_home + "/bin/svace")
            run_build = cmd_build("build", self.settings.jack_option, self.settings.verbose,
                                  "--hash-server-memory", self.settings.hash_server_memory,
                                  "--svace-dir", self.work_folder, self.settings.build_cmd,
                                  _err=sys.stderr, _out=sys.stdout)
        except sh.ErrorReturnCode_255:
            sys.stderr.write("Svace exited with error code 255. No build object found.\n")
            return 2
        except Exception as e:
            sys.stderr.write(unicode(e))
            return 2
        return self.analyze()
