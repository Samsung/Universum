import glob
import json
import os
import urllib.parse
from copy import deepcopy
from typing import Dict, List, Optional, TextIO, Tuple

from . import artifact_collector, reporter
from .output import HasOutput
from .project_directory import ProjectDirectory
from .structure_handler import HasStructure
from ..configuration_support import Configuration
from ..lib import utils
from ..lib.gravity import Dependency
from ..lib.utils import make_block


class CodeReportCollector(ProjectDirectory, HasOutput, HasStructure):
    reporter_factory = Dependency(reporter.Reporter)
    artifacts_factory = Dependency(artifact_collector.ArtifactCollector)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.artifacts: artifact_collector.ArtifactCollector = self.artifacts_factory()
        self.reporter: reporter.Reporter = self.reporter_factory()
        self.report_path: str = ""
        self.repo_diff: Optional[List[Tuple[Optional[str], Optional[str], Optional[str]]]]

    def prepare_environment(self, project_config: Configuration) -> Configuration:
        afterall_steps: Configuration = Configuration()
        for item in project_config.configs:
            if item.children:
                afterall_steps += self.prepare_environment(item.children)
            if not item.code_report:
                continue
            if not self.report_path:
                self.report_path = os.path.join(self.settings.project_root, "code_report_results")
                if not os.path.exists(self.report_path):
                    os.makedirs(self.report_path)
            temp_filename: str = "${CODE_REPORT_FILE}"
            name: str = utils.calculate_file_absolute_path(self.report_path, item.name) + ".json"
            actual_filename: str = os.path.join(self.report_path, name)

            item.replace_string(temp_filename, actual_filename)
            afterall_steps += [deepcopy(item)]
        return afterall_steps

    def _report_as_pylint_json(self, report) -> int:
        for result in report:
            text = result["symbol"] + ": " + result["message"]
            path = result["path"]
            message: reporter.ReportMessage = {"message": text, "line": int(result["line"])}
            self.reporter.code_report(path, message)
        return len(report)

    def _report_as_sarif_json(self, report) -> int:
        version: str = report.get('version', '')
        if version != '2.1.0':
            raise ValueError(f"Version {version} is not supported")
        issue_count: int = 0
        for run in report.get('runs', []):
            analyzer_data: Dict[str, str] = run.get('tool').get('driver')  # non-optional per definition
            who: str = f"{analyzer_data.get('name')} [{analyzer_data.get('version', '?')}]"
            for issue in run.get('results', []):
                issue_count += 1
                what: str = issue.get('message')
                for location in issue.get('locations', []):
                    location_data: Dict[str, Dict[str, str]] = location.get('physicalLocation')
                    if not location_data:
                        continue
                    artifact_data = location_data.get('artifactLocation')
                    if not artifact_data:
                        if location_data.get('address'):
                            continue  # binary artifact can't be processed
                        raise ValueError("Unexpected lack of artifactLocation tag")
                    path: str = urllib.parse.unquote(artifact_data.get('uri', ''))
                    region_data = location_data.get('region')
                    if not region_data:
                        continue  # TODO: cover this case as comment to the file as a whole
                    message: reporter.ReportMessage = {"message": f"{who} : {what}",
                                                       "line": int(region_data.get('startLine', '0'))}
                    self.reporter.code_report(path, message)
        return issue_count

    @make_block("Processing code report results")
    def report_code_report_results(self) -> None:
        reports: List[str] = glob.glob(self.report_path + "/*.json")
        for report_file in reports:
            with open(report_file, "r", encoding="utf-8") as f:
                text: str = f.read()
                report: Optional[List[Dict[str, str]]] = None
                if text:
                    report = json.loads(text)

            issue_count: int
            if not report and report != []:
                self.out.log_error("There are no results in code report file. Something went wrong.")
                continue

            try:
                issue_count = self._report_as_sarif_json(report)
            except (KeyError, AttributeError, ValueError):
                try:
                    issue_count = self._report_as_pylint_json(report)
                except (KeyError, AttributeError, ValueError):
                    self.out.log_error("Could not parse report file. Something went wrong.")
                    continue

            if issue_count != 0:
                text = str(issue_count) + " issues"
                self.out.log_error("Found " + text)
                self.out.set_build_status(os.path.splitext(os.path.basename(report_file))[0] + ": " + text)
            else:
                self.out.log("Issues not found.")
