# -*- coding: UTF-8 -*-

import glob
import json
import os

from .output import needs_output
from . import artifact_collector, reporter
from ..lib.gravity import Dependency, Module
from ..lib.utils import make_block
from .structure_handler import needs_structure


@needs_output
@needs_structure
class CodeReportCollector(Module):
    reporter_factory = Dependency(reporter.Reporter)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    def __init__(self, *args, **kwargs):
        super(CodeReportCollector, self).__init__(*args, **kwargs)
        self.artifacts = self.artifacts_factory()
        self.reporter = self.reporter_factory()
        self.report_path = ""

    def set_code_report_directory(self, project_root):
        if self.report_path:
            return
        self.report_path = os.path.join(project_root, "code_report_results")
        if not os.path.exists(self.report_path):
            os.makedirs(self.report_path)

    def prepare_env_for_code_report(self, item, project_root):
        if not item.get("code_report", False):
            return item

        self.set_code_report_directory(project_root)
        temp_filename = "${CODE_REPORT_FILE}"
        for enum, i in enumerate(item["command"]):
            if temp_filename in i:
                item["command"][enum] = item["command"][enum].replace(temp_filename,
                                        os.path.join(self.report_path, item.get("name").replace(" ", "_") + ".json"))
        return item

    @make_block("Processing code report results")
    def report(self):
        reports = glob.glob(self.report_path + "/*.json")
        for report_file in reports:
            with open(report_file, "r") as f:
                report = json.loads(f.read())

            json_file = self.artifacts.create_text_file("Static_analysis_report.json")
            json_file.write(json.dumps(report, indent=4))

            for result in report:
                text = result["symbol"] + ": " + result["message"]
                self.reporter.code_report(result["path"], {"message": text, "line": result["line"]})

            if report:
                text = unicode(len(report)) + " issues"
                self.out.log_stderr("Found " + text)
                self.out.report_build_status(os.path.basename(report_file) + ": " + text)

        if not reports:  # e.g. required module is not installed (pylint, load-plugins for pylintrc)
            self.out.log("Issues not found.")

    def report_code_report_results(self):
        if os.path.exists(self.report_path):
            self.report()
