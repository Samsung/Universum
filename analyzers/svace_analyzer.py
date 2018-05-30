# -*- coding: UTF-8 -*-

import json
import os
import sh
import sys
from lxml import etree

__all__ = ["SvaceAnalyzer"]


class SvaceAnalyzer(object):

    @staticmethod
    def define_arguments(parser, args):
        parser.add_argument("--build-path", dest="build_path", help="Path to directory, "
                            "from where you should build project.")
        parser.add_argument("--build-cmd", dest="build_cmd", nargs='+',
                            help="Relative path to build script or command itself.")
        parser.add_argument("--lang", dest="lang", choices=["JAVA", "CXX"], help="Language to analyze.")
        return parser.parse_args(args)

    def __init__(self, settings, static_analyzer):
        self.settings = settings
        self.settings.static_analyzer = static_analyzer

        self.settings.svace_home = "/opt/svace-x64-linux"
        self.settings.product = "Svace_build_home"
        self.settings.build_path = os.path.join(os.getcwd(), settings.build_path)
        self.work_folder = os.path.join(os.getcwd(), self.settings.product)
        self.settings.jack_option = "--enable-jack-interception"
        self.settings.hash_server_memory = "2048"
        self.settings.verbose = "--verbose"

        if self.settings.lang == "JAVA":
            self.disabled_language = "cxx"
            self.enabled_language = "java"
        elif self.settings.lang == "CXX":
            self.disabled_language = "java"
            self.enabled_language = "cxx"

    def analyze(self):
        try:
            cmd_analyze = sh.Command(self.settings.svace_home + "/bin/svace")
            run_analyze = cmd_analyze("analyze", "-q", "--svace-dir", self.work_folder, "--disable-language",
                                      self.disabled_language, "--enable-language", self.enabled_language,
                                      "--preset", self.enabled_language)

            svres_full = os.path.join(self.work_folder, "analyze-res", self.settings.product + ".svres")
            root = etree.parse(svres_full)

            warn_info = root.xpath('//WarnInfo')
            warn_info_ex = root.xpath('//WarnInfoEx')
            issues_loads = []
            warn_result = []

            for info in warn_info:
                for info_extended in warn_info_ex:
                    if info.attrib["id"] == info_extended.attrib["id"]:
                        warn_result.append((info, info_extended))

            for info, info_extended in warn_result:
                trace_info = info_extended.xpath("traces/RoleTraceInfo")
                msg = []
                for role in trace_info:
                    loc_info = role.xpath("locations/LocInfo")
                    msg.append("[" + role.attrib["role"] + "] " + loc_info[0].attrib["file"] + ": " +
                               loc_info[0].attrib["line"])

                issue = dict()
                issue["symbol"] = info.attrib["warnClass"]
                issue["message"] = "\n" + "Warning message: " + info.attrib["msg"]
                issue["path"] = info.attrib["file"]
                issue["line"] = info.attrib["line"]
                issues_loads.append(issue)
            sys.stdout.write(json.dumps(issues_loads))
        except Exception as e:
            sys.stderr.write(e.message)
            return 1
        return 0

    def send_to_ftp(self):
        pass

    def execute(self):

        if not os.path.exists(self.settings.svace_home):
            sys.stderr.write("SVACE_HOME=" + self.settings.svace_home + " folder doesn't exist.")
            return 1

        try:
            cmd_init = sh.Command(self.settings.svace_home + "/bin/svace")
            run_init = cmd_init("init", "-f", "--shared=all", "--bare", self.work_folder)
            os.chdir(self.work_folder)
            cmd_build = sh.Command(self.settings.svace_home + "/bin/svace")
            run_build = cmd_build("build", self.settings.jack_option, self.settings.verbose,
                                  "--hash-server-memory", self.settings.hash_server_memory,
                                  "--svace-dir", self.work_folder, self.settings.build_cmd,
                                  _cwd=self.settings.build_path)
        except OSError as e:
            sys.stderr.write(str(e))
            return 1
        except Exception as e:
            sys.stderr.write(e.stderr)
            return 1
        return self.analyze()
