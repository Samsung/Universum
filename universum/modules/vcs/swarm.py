import os
import urllib3

from ...lib.ci_exception import CiException
from ...lib.gravity import Module, Dependency
from ...lib.module_arguments import IncorrectParameterError
from ...lib import utils
from ..reporter import ReportObserver, Reporter
from ..output import HasOutput

urllib3.disable_warnings((urllib3.exceptions.InsecurePlatformWarning, urllib3.exceptions.SNIMissingWarning))


__all__ = [
    "Swarm"
]


class Swarm(ReportObserver, HasOutput):
    """
    This class contains CI functions for interaction with Swarm via 'swarm_cli.py'
    """
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Swarm",
                                                     "Parameters for performing a test run for pre-commit review")
        parser.add_argument("--swarm-server-url", "-ssu", dest="server_url", metavar="SWARM_SERVER",
                            help="Swarm server URL; is used for additional interaction such as voting for the review")
        parser.add_argument("--swarm-review-id", "-sre", dest="review_id", metavar="REVIEW",
                            help="Swarm review number; is sent by Swarm triggering link as '{review}'")
        parser.add_argument("--swarm-change", "-sch", dest="change", metavar="SWARM_CHANGELIST",
                            help="Swarm change list to unshelve; is sent by Swarm triggering link as '{change}'")
        parser.add_argument("--swarm-pass-link", "-spl", dest="pass_link", metavar="PASS",
                            help="Swarm 'success' link; is sent by Swarm triggering link as '{pass}'")
        parser.add_argument("--swarm-fail-link", "-sfl", dest="fail_link", metavar="FAIL",
                            help="Swarm 'fail' link; is sent by Swarm triggering link as '{fail}'")

    def __init__(self, user, password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.password = password
        self.review_version = None
        self.review_latest_version = None
        self.client_root = ""
        self.mappings_dict = {}

        utils.check_required_option(self.settings, "server_url", """
            the URL of the Swarm server is not specified.

            The URL is needed for communicating with swarm code review system:
            getting review revision, posting comments, voting. Please specify
            the server URL by using '--swarm-server-url' ('-ssu') command
            line parameter or by setting SWARM_SERVER environment variable.""")
        utils.check_required_option(self.settings, "review_id", """
            the Swarm review number is not specified.

            The review number is needed for communicating with swarm code review system:
            getting review revision, posting comments, voting. Please specify the number
            by using '--swarm-review-id' ('-sre') command line parameter or by setting
            REVIEW environment variable.

            In order to setup sending of the review number for pre-commit in Swarm,
            please use the '{review}' argument in Automated Tests field of the Project
            Settings.
            """)
        utils.check_required_option(self.settings, "change", """
            the Swarm changelist for unshelving is not specified.

            The changelist is used for unshelving change before build and for
            determining review revision. Please specify the changelist by using
            '--swarm-change' ('-sch') command line parameter or by setting
            SWARM_CHANGELIST environment variable.

            In order to setup sending of the review number for pre-commit in Swarm,
            please use the '{change}' argument in Automated Tests field of the Project
            Settings.
            """)

        if " " in self.settings.change or "," in self.settings.change:
            raise IncorrectParameterError("the Swarm changelist for unshelving is incorrect.\n\n"
                                          "The changelist parameter must only contain one number. Please specify the\n"
                                          "changelist by using '--swarm-change' ('-sch') command line parameter or by\n"
                                          "setting SWARM_CHANGELIST environment variable.")

        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)

    def get_review_link(self):
        return self.settings.server_url + "/reviews/" + self.settings.review_id + "/"

    def update_review_version(self):
        if self.review_version and self.review_latest_version:
            return

        result = utils.make_request(self.settings.server_url + "/api/v2/reviews/" + str(self.settings.review_id),
                                    critical=False, data={"id": self.settings.review_id}, auth=(self.user, self.password))
        try:
            versions = result.json()["review"]["versions"]
        except (KeyError, ValueError) as e:
            text = "Error parsing Swarm server response. Full response is the following:\n"
            text += result.text
            raise CiException(text) from e

        self.review_latest_version = str(len(versions))

        for index, entry in enumerate(versions):
            if int(entry["change"]) == int(self.settings.change):
                self.review_version = str(index + 1)
                return

        try:
            last_cl = int(versions[int(self.review_latest_version) - 1]["archiveChange"])
            if last_cl == int(self.settings.change):
                self.review_version = self.review_latest_version
        except KeyError:
            pass

    def is_latest_version(self):
        self.update_review_version()

        if self.review_latest_version == self.review_version:
            return True

        text = "Current review version is {0}, while latest review version is already {1}".format(
            self.review_version, self.review_latest_version)
        self.out.log(text)
        return False

    def post_comment(self, text, filename=None, line=None, version=None, no_notification=False):
        request = {"body": text,
                   "topic": "reviews/" + str(self.settings.review_id)}
        if filename:
            request["context[file]"] = filename
            if line:
                request["context[rightLine]"] = line
            if version:
                request["context[version]"] = version
            if no_notification:
                request["silenceNotification"] = "true"

        utils.make_request(self.settings.server_url + "/api/v9/comments", request_method="POST", critical=False,
                           data=request, auth=(self.user, self.password))

    def vote_review(self, result, version=None):
        request = {}
        if result:
            request["vote[value]"] = "up"
        else:
            request["vote[value]"] = "down"
        if version:
            request["vote[version]"] = version

        utils.make_request(self.settings.server_url + "/api/v6/reviews/" + self.settings.review_id, critical=False,
                           request_method="PATCH", data=request, auth=(self.user, self.password))

    def report_start(self, report_text):
        self.update_review_version()
        if self.review_version:
            report_text += "\nStarted build for review revision #" + self.review_version
        self.post_comment(report_text)

    def code_report_to_review(self, report):
        for path, issues in report.items():
            abs_path = os.path.join(self.client_root, path)
            if abs_path in self.mappings_dict:
                for issue in issues:
                    self.post_comment(issue['message'],
                                      filename=self.mappings_dict[abs_path],
                                      line=issue['line'],
                                      no_notification=True)

    def report_result(self, result, report_text=None, no_vote=False):
        # Opening links, sent by Swarm
        # Does not require login to Swarm; changes "Automated Tests" icon
        # Should not be applied to non-latest revision
        if result:
            link = self.settings.pass_link
        else:
            link = self.settings.fail_link

        if self.is_latest_version():
            if link is not None:
                self.out.log("Build status on Swarm will be updated via URL " + link)
                utils.make_request(link, critical=False)
            else:
                self.out.log("Build status on Swarm will not be updated because " +
                             "the '{0}' link has not been provided.".format("PASS" if result else "FAIL"))
        else:
            text = "Build status on Swarm will not be updated because tested review revision is not latest."
            if not link:
                text += " Also, even if the review revision was latest, we wouldn't be able to report the status " \
                        "because the '{0}' link has not been provided.".format("PASS" if result else "FAIL")
            self.out.log(text)

        # Voting up or down; posting comments if any
        # An addition to "Automated Tests" functionality, requires login to Swarm
        self.update_review_version()
        if not no_vote:
            self.vote_review(result, version=self.review_version)
        if report_text:
            if self.review_version:
                report_text = "This is a build result for review revision #" + self.review_version + "\n" + report_text
            self.post_comment(report_text)
