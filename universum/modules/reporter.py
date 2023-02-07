from collections import defaultdict
from typing import Dict, List, Tuple
from typing_extensions import TypedDict

from . import automation_server
from .output import HasOutput
from .structure_handler import HasStructure, Block
from ..lib.ci_exception import CiException
from ..lib.gravity import Dependency
from ..lib.utils import make_block

__all__ = [
    "ReportObserver",
    "Reporter"
]

ReportMessage = TypedDict('ReportMessage', {'message': str, 'line': int})


class ReportObserver:
    """
    Abstract base class for reporting modules
    """

    def get_review_link(self):
        raise NotImplementedError

    def report_start(self, report_text):
        raise NotImplementedError

    def report_result(self, result, report_text=None, no_vote=False):
        raise NotImplementedError

    def code_report_to_review(self, report: Dict[str, List[ReportMessage]]) -> None:
        raise NotImplementedError


class Reporter(HasOutput, HasStructure):
    automation_server_factory = Dependency(automation_server.AutomationServerForHostingBuild)

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
        parser.add_argument("--report-only-fails-short", "-rofs", action="store_true", dest="only_fails_short",
                            help="Include only the short list of failed steps to reporting comments")
        parser.add_argument("--report-no-vote", "-rnv", action="store_true", dest="no_vote",
                            help="Do not vote up/down review depending on result")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.observers: List = []
        self.report_initialized: bool = False
        self.blocks_to_report: List = []
        self.artifacts_to_report: List = []
        self.code_report_comments: Dict[str, List[ReportMessage]] = defaultdict(list)

        self.automation_server = self.automation_server_factory()

    def subscribe(self, observer):
        self.observers.append(observer)

    def report_review_link(self):
        for observer in self.observers:
            self.out.log("Review can be found here: " + observer.get_review_link())

    @make_block("Reporting build start", pass_errors=False)
    def report_build_started(self):
        self.report_initialized = True
        if not self.observers:
            self.out.log("Nowhere to report. Skipping...")
            return

        if not self.settings.report_start:
            self.out.log("Reporting skipped. To report build start, use '--report-build-start' option")
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

    def code_report(self, path: str, message: ReportMessage) -> None:
        self.code_report_comments[path].append(message)

    def _report_build_result(self) -> bool:
        if self.report_initialized is False:
            self.out.log("Not reporting: no build steps executed")
            return False

        if self.settings.only_fails_short:
            self.settings.only_fails = True

        is_successful = True
        text = "Here is the summarized build result:\n"
        self.out.log(text)
        for step in self.blocks_to_report:
            text, status = self._report_steps_recursively(step, text, "")
            is_successful = is_successful and status
        if self.settings.only_fails and is_successful:
            text += "  All steps succeeded"
            self.out.log("  All steps succeeded")

        if not self.observers:
            self.out.log("Nowhere to report. Skipping...")
            return is_successful

        if is_successful:
            self.out.log("Reporting successful build...")
            if not self.settings.report_success:
                text = "Sending comment skipped. " + \
                       "To report build success, use '--report-build-success' option"
                self.out.log(text)
                text = ""
        else:
            self.out.log("Reporting failed build...")

        if text:
            if not self.settings.report_start:
                text += "\n\n" + self.automation_server.report_build_location()

            if self.artifacts_to_report:
                text += "\n\nThe following artifacts were generated during check:\n"
                for item in self.artifacts_to_report:
                    text += "* " + item + "\n"
                text += "Please take a look."

            for observer in self.observers:
                observer.report_result(is_successful, text, no_vote=self.settings.no_vote)

        if self.code_report_comments:
            self.out.log("Reporting code report issues ")
            for observer in self.observers:
                observer.code_report_to_review(self.code_report_comments)

        return is_successful

    @make_block("Reporting build result")
    def report_build_result(self) -> bool:
        try:
            return self._report_build_result()
        except CiException as e:
            self.out.log_error(str(e))
            self.structure.fail_current_block()
            return False

    def _report_steps_recursively(self, block: Block, text: str, indent: str) -> Tuple[str, bool]:
        has_children: bool = bool(block.children)
        block_title: str = block.number + ' ' + block.name
        if not self.settings.only_fails:
            text += indent + str(block) + '\n'
            self.out.log_summary_step(indent + block_title, has_children, block.status)
        elif not block.is_successful():
            if not self.settings.only_fails_short or not has_children:
                text += str(block) + '\n'
                self.out.log_summary_step(block_title, has_children, block.status)

        is_successful = block.is_successful()
        for child in block.children:
            text, status = self._report_steps_recursively(child, text, indent + "  ")
            is_successful = is_successful and status
        return text, is_successful
