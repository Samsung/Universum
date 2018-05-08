# -*- coding: UTF-8 -*-

from collections import defaultdict
from .automation_server import AutomationServer
from .gravity import Module, Dependency
from .output import needs_output
from .structure_handler import needs_structure
from .utils import make_block

__all__ = [
    "ReportObserver",
    "Reporter"
]


def report_steps_recursively(block, text, indent, only_fails=False):
    text_status, is_successful = block.get_full_status()
    if only_fails:
        if not is_successful:
            text += text_status + "\n"
    else:
        text += indent + text_status + "\n"
    for substep in block.children:
        text, status = report_steps_recursively(substep, text, indent + "  ", only_fails)
        is_successful = is_successful and status
    return text, is_successful


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
@needs_structure
class Reporter(Module):
    automation_server_factory = Dependency(AutomationServer)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Result reporting",
                                                     "Build results collecting and publishing parameters")

        parser.add_argument("--report-build-start", "-rst", action="store_true", dest="report_start",
                            help="Send additional comment to review system on build started (with link to log)")
        parser.add_argument("--report-build-success", "-rsu", action="store_true", dest="report_success",
                            help="Send comment to review system on build success (in addition to vote up)")
        parser.add_argument("--report-only-fails", "-rof", action="store_true", dest="only_fails",
                            help="Include only the list of failed steps to reporting comments")

    def __init__(self, settings):
        self.settings = settings

        self.observers = []
        self.report_initialized = False
        self.blocks_to_report = []
        self.artifacts_to_report = []
        self.code_report_comments = defaultdict(list)

        self.automation_server = self.automation_server_factory()

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
        text += self.automation_server.report_build_location()
        text += "\n\nPlease do not submit until revision testing is finished."

        for observer in self.observers:
            observer.report_start(text)

    def add_block_to_report(self, block):
        self.blocks_to_report.append(block)

    def report_artifacts(self, artifact_list):
        self.artifacts_to_report.extend(artifact_list)

    def code_report(self, path, message):
        self.code_report_comments[path].append(message)

    @make_block("Reporting build result", pass_errors=False)
    def report_build_result(self):
        if self.report_initialized is False:
            self.out.log("Not reporting: no build steps executed")
            return

        is_successful = True
        text = "Here is the summarized build result:\n"
        for step in self.blocks_to_report:
            text, status = report_steps_recursively(step, text, "", self.settings.only_fails)
            is_successful = is_successful and status
        if self.settings.only_fails and is_successful:
            text += "  All steps succeeded"

        self.out.log(text)
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
            text += "\n\n" + self.automation_server.report_build_location()

        if self.artifacts_to_report:
            text += "\n\nThe following artifacts were generated during check:\n"
            for item in self.artifacts_to_report:
                text += "* " + item + "\n"
            text += "Please take a look."

        for observer in self.observers:
            observer.report_result(is_successful, text)

        if self.code_report_comments:
            self.out.log("Reporting code report issues ")
            for observer in self.observers:
                observer.code_report_to_review(self.code_report_comments)
