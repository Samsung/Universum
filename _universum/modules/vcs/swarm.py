# -*- coding: UTF-8 -*-

import os
import urllib
import urllib3
import requests

from ...lib.ci_exception import CiException
from ...lib.gravity import Module, Dependency
from ...lib.module_arguments import IncorrectParameterError
from ...lib import utils
from ..reporter import ReportObserver, Reporter
from ..output import needs_output

urllib3.disable_warnings((urllib3.exceptions.InsecurePlatformWarning, urllib3.exceptions.SNIMissingWarning))


__all__ = [
    "Swarm"
]


def check_request_result(result):
    if result.status_code != 200:
        text = "Invalid return code " + result.status_code + ". Response is:\n"
        text += result.text
        raise CiException(text)


@needs_output
class Swarm(ReportObserver, Module):
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

    def check_required_option(self, name, env_var):
        utils.check_required_option(self.settings, name, env_var)

    def __init__(self, user, password, *args, **kwargs):
        super(Swarm, self).__init__(*args, **kwargs)
        self.user = user
        self.password = password
        self.review_version = None
        self.review_latest_version = None
        self.client_root = ""
        self.mappings_dict = {}

        self.check_required_option("review_id", "REVIEW")
        self.check_required_option("server_url", "SWARM_SERVER")
        self.check_required_option("change", "SWARM_CHANGELIST")

        if " " in self.settings.change or "," in self.settings.change:
            raise IncorrectParameterError("SWARM_CHANGELIST takes only one CL number")

        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)

    def get_review_link(self):
        return self.settings.server_url + "/reviews/" + self.settings.review_id + "/"

    def update_review_version(self):
        if self.review_version:
            return

        result = requests.get(self.settings.server_url + "/api/v2/reviews/" + unicode(self.settings.review_id),
                              data={"id": self.settings.review_id}, auth=(self.user, self.password))
        try:
            versions = result.json()["review"]["versions"]
        except (KeyError, ValueError):
            text = "Error parsing Swarm server response. Full response is the following:\n"
            text += result.text
            raise CiException(text)

        self.review_latest_version = unicode(len(versions))

        for index, entry in enumerate(versions):
            if int(entry["change"]) == int(self.settings.change):
                self.review_version = unicode(index + 1)
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

        text = "Current review version is " + self.review_version + \
               ", while latest review version is already " + self.review_latest_version
        self.out.log(text)
        return False

    def post_comment(self, text, filename=None, line=None, version=None, no_notification=False):
        request = {"body": text,
                   "topic": "reviews/" + unicode(self.settings.review_id)}
        if filename:
            request["context[file]"] = filename
            if line:
                request["context[rightLine]"] = line
            if version:
                request["context[version]"] = version
            if no_notification:
                request["silenceNotification"] = "true"

        result = requests.post(self.settings.server_url + "/api/v9/comments", data=request,
                               auth=(self.user, self.password))
        check_request_result(result)

    def vote_review(self, result, version=None):
        request = {}
        if result:
            request["vote[value]"] = "up"
        else:
            request["vote[value]"] = "down"
        if version:
            request["vote[version]"] = version

        result = requests.patch(self.settings.server_url + "/api/v6/reviews/" + self.settings.review_id,
                                data=request, auth=(self.user, self.password))
        check_request_result(result)

    def report_start(self, report_text):
        self.update_review_version()
        if self.review_version:
            report_text += "\nStarted build for review revision #" + self.review_version
        self.post_comment(report_text)

    def code_report_to_review(self, report):
        for path, issues in report.iteritems():
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
        if result:
            link = self.settings.pass_link
        else:
            link = self.settings.fail_link

        try:
            if link is not None:
                self.out.log("Swarm will be informed about build status by URL " + link)
                urllib.urlopen(link)
            else:
                self.out.log("Swarm will not be informed about build status because " + \
                             "the '{0}' link was not provided".format("PASS" if result else "FAIL"))
        except IOError as e:
            if e.args[0] == "http error":
                text = "HTTP error " + unicode(e.args[1]) + ": " + e.args[2]
            else:
                text = unicode(e)
            text += "\nPossible reasons of this error:" + \
                    "\n * Network errors" + \
                    "\n * Swarm parameters ('PASS'/'FAIL' links) retrieved or parsed incorrectly"
            raise CiException(text)

        # Voting up or down; posting comments if any
        # An addition to "Automated Tests" functionality, requires login to Swarm
        self.update_review_version()
        if not no_vote:
            self.vote_review(result, version=self.review_version)
        if report_text:
            if self.review_version:
                report_text = "This is a build result for review revision #" + self.review_version + "\n" + report_text
            self.post_comment(report_text)
