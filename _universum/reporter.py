# -*- coding: UTF-8 -*-

from collections import defaultdict
from . import jenkins_driver, teamcity_driver, local_driver, utils
from .gravity import Module, Dependency
from .output import needs_output
from .utils import make_block

__all__ = [
    "ReportObserver",
    "Reporter"
]


class ReportObserver(object):
    """
    Abstract base class for reporting modules.
    """

    def __init__(self, *args, **kwargs):
        self.super_init(ReportObserver, *args, **kwargs)

    def report_start(self, report_text):
        raise NotImplementedError

    def report_result(self, result, report_text=None):
        raise NotImplementedError

    def code_report_to_review(self, report):
        raise NotImplementedError


@needs_output
class Reporter(Module):
    teamcity_info_factory = Dependency(teamcity_driver.TeamCityBuildInfo)
    local_info_factory = Dependency(local_driver.LocalBuildInfo)
    jenkins_info_factory = Dependency(jenkins_driver.JenkinsBuildInfo)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Result reporting",
                                                     "Build results collecting and publishing parameters")
        parser.add_argument("--report-env", "-re", dest="env", choices=["tc", "jenkins", "local"],
                            help="Type of environment to refer to (tc - TeamCity, jenkins - Jenkins, "
                                 "local - user local terminal). "
                                 "TeamCity environment is detected automatically when launched on build agent")

        parser.add_argument("--report-build-start", "-rst", action="store_true", dest="report_start",
                            help="Send additional comment to review system on build started (with link to log)")
        parser.add_argument("--report-build-success", "-rsu", action="store_true", dest="report_success",
                            help="Send comment to review system on build success (in addition to vote up)")

    def __init__(self, settings):
        self.settings = settings
        self.driver = utils.create_diver(teamcity_factory=self.teamcity_info_factory,
                                         jenkins_factory=self.jenkins_info_factory,
                                         local_factory=self.local_info_factory,
                                         default=settings.env)

        self.observers = []
        self.report_initialized = False
        self.steps_to_report = []
        self.artifacts_to_report = []
        self.local_artifacts_dir = None
        self.code_report_comments = defaultdict(list)

    def subscribe(self, observer):
        self.observers.append(observer)

    @make_block("Reporting build start", pass_errors=False)
    def report_build_started(self):
        self.report_initialized = True
        if not self.observers:
            self.out.log("Nowhere to report. Skipping...")
            return

        if not self.settings.report_start:
            self.out.log("Skipped. To report build start, use '--report-build-start' option")
            return

        text = "Review update detected!\n\n"
        text += self.driver.report_build_location()
        text += "\n\nPlease do not submit until revision testing is finished."

        for observer in self.observers:
            observer.report_start(text)

    def report_build_step(self, name, result):
        self.steps_to_report.append([name, result])

    def report_artifacts(self, local_artifacts_dir, artifact_list):
        self.local_artifacts_dir = local_artifacts_dir
        self.artifacts_to_report.extend(artifact_list)

    def code_report(self, path, message):
        self.code_report_comments[path].append(message)

    @make_block("Reporting build result", pass_errors=False)
    def report_build_result(self):
        if self.report_initialized is False:
            self.out.log("Not reporting: no build steps executed")
            return

        is_successful = True
        text = "The following steps were checked:\n"
        for name, result in self.steps_to_report:
            text += name
            if result:
                text += " - SUCCEEDED\n"
            else:
                text += " - FAILED\n"
                is_successful = False

        if not self.observers:
            self.out.log("Nowhere to report. Skipping...")
            return

        if is_successful:
            self.out.log("Reporting successful build...")
            if not self.settings.report_success:
                text = "Sending comment skipped." + \
                       "To report build success, use '--report-build-success' option"
                self.out.log(text)
                text = None
        else:
            self.out.log("Reporting failed build...")
            if not self.settings.report_start:
                text += "\n" + self.driver.report_build_location()

        if self.artifacts_to_report:
            text += "\n\nThe following artifacts were generated during check:\n"
            for item in self.artifacts_to_report:
                text += "* " + self.driver.artifact_path(self.local_artifacts_dir, item) + "\n"
            text += "Please take a look."

        for observer in self.observers:
            observer.report_result(is_successful, text)

        if self.code_report_comments:
            self.out.log("Reporting code report issues ")
            for observer in self.observers:
                observer.code_report_to_review(self.code_report_comments)
