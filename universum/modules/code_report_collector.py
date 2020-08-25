from copy import deepcopy
from typing import Dict, List, Optional, TextIO, Tuple
import glob
import json
import os

from universum.configuration_support import Variations
from .output import HasOutput
from .project_directory import ProjectDirectory
from . import artifact_collector, reporter
from ..lib import utils
from ..lib.gravity import Dependency
from ..lib.utils import make_block
from .structure_handler import HasStructure


class CodeReportCollector(ProjectDirectory, HasOutput, HasStructure):
    reporter_factory = Dependency(reporter.Reporter)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.artifacts: artifact_collector.ArtifactCollector = self.artifacts_factory()
        self.reporter: reporter.Reporter = self.reporter_factory()
        self.report_path: str = ""
        self.repo_diff: List[Tuple[Optional[str], Optional[str], Optional[str]]]

    def set_code_report_directory(self, project_root):
        if self.report_path:
            return
        self.report_path = os.path.join(project_root, "code_report_results")
        if not os.path.exists(self.report_path):
            os.makedirs(self.report_path)

    def prepare_environment(self, project_configs):
        afterall_steps = []
        for item in project_configs:
            if not item.get("code_report", False):
                continue

            self.set_code_report_directory(self.settings.project_root)
            temp_filename = "${CODE_REPORT_FILE}"
            name = utils.calculate_file_absolute_path(self.report_path, item.get("name")) + ".json"
            actual_filename = os.path.join(self.report_path, name)

            for key in item:
                if key == "command":
                    item[key] = [word.replace(temp_filename, actual_filename) for word in item[key]]
                else:
                    try:
                        item[key] = item[key].replace(temp_filename, actual_filename)
                    except AttributeError as error:
                        if "object has no attribute 'replace'" not in str(error):
                            raise

            afterall_item = deepcopy(item)
            afterall_steps.append(afterall_item)
        return Variations(afterall_steps)

    @make_block("Processing code report results")
    def report_code_report_results(self) -> None:
        reports: List[str] = glob.glob(self.report_path + "/*.json")
        for report_file in reports:
            with open(report_file, "r") as f:
                text: str = f.read()
                report: Optional[List[Dict[str, str]]] = None
                if text:
                    report = json.loads(text)

            json_file: TextIO = self.artifacts.create_text_file("Static_analysis_report.json")
            json_file.write(json.dumps(report, indent=4))

            if report:
                for result in report:
                    text = result["symbol"] + ": " + result["message"]
                    self.reporter.code_report(result["path"], {"message": text, "line": result["line"]})

            if report:
                text = str(len(report)) + " issues"
                self.out.log_stderr("Found " + text)
                self.out.report_build_status(os.path.splitext(os.path.basename(report_file))[0] + ": " + text)
            elif report == []:
                self.out.log("Issues not found.")
            else:  # if nothing was written to file
                self.out.log_stderr("There are no results in code report file. Something went wrong.")
