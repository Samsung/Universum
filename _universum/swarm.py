# -*- coding: UTF-8 -*-

import os
import urllib
import urllib3

from . import swarm_cli
from .ci_exception import CiException
from .gravity import Module, Dependency
from .module_arguments import IncorrectParameterError
from .reporter import ReportObserver, Reporter

urllib3.disable_warnings((urllib3.exceptions.InsecurePlatformWarning, urllib3.exceptions.SNIMissingWarning))


__all__ = [
    "Swarm"
]


class Swarm(ReportObserver, Module):
    reporter_factory = Dependency(Reporter)

    """
    This class contains CI functions for interaction with Swarm via 'swarm_cli.py'
    """
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Swarm",
                                                     "Parameters for performing a test run for pre-commit review")
        parser.add_argument("--swarm-server-url", "-ssu", dest="server_url", metavar="SWARM_SERVER",
                            help="Swarm server URL; is used for additional interaction such as voting for the review")
        parser.add_argument("--swarm-review-id", "-sre", dest="review_id", metavar="REVIEW",
                            help="Swarm review number; is sent by Swarm triggering link as '{review}'")
        parser.add_argument("--swarm-pass-link", "-spl", dest="pass_link", metavar="PASS",
                            help="Swarm 'success' link; is sent by Swarm triggering link as '{pass}'")
        parser.add_argument("--swarm-fail-link", "-sfl", dest="fail_link", metavar="FAIL",
                            help="Swarm 'fail' link; is sent by Swarm triggering link as '{fail}'")

    def check_required_option(self, name, env_var):
        if getattr(self.settings, name) is None:
            text = "'" + env_var + "' variable was not retrieved correctly." \
                   "\nPlease make sure Swarm has passed required parameters to corresponding environment variables " \
                   "or, for debug purposes, set them manually"
            raise IncorrectParameterError(text)

    def __init__(self, settings, user, password, **kwargs):
        self.super_init(Swarm, **kwargs)
        self.settings = settings
        self.user = user
        self.password = password
        self.session = None
        self.client_root = ""
        self.mappings_dict = {}

        if not self.settings.server_url:
            raise IncorrectParameterError("Please set up '--swarm-server-url' for correct interaction with Swarm")

        self.check_required_option("review_id", "REVIEW")
        self.check_required_option("pass_link", "PASS")
        self.check_required_option("fail_link", "FAIL")

        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)

    def get_review_link(self):
        return self.settings.server_url + "/reviews/" + self.settings.review_id + "/"

    def get_swarm_session(self):
        if self.session is None:
            self.session = swarm_cli.create_session(self.user,
                                                    self.password,
                                                    self.settings.server_url)

    def report_start(self, report_text):
        self.get_swarm_session()
        self.session.post_comment(self.settings.review_id, report_text)

    def code_report_to_review(self, report):
        # There is a possibility to make an independent call for the code report,
        # so we should check if the session is alive
        self.get_swarm_session()
        for path, issues in report.iteritems():
            abs_path = os.path.join(self.client_root, path)
            if abs_path in self.mappings_dict:
                for issue in issues:
                    self.session.post_comment(self.settings.review_id, issue['message'],
                                              self.mappings_dict[abs_path], issue['line'])

    def report_result(self, result, report_text=None):

        # Opening links, sent by Swarm
        # Does not require login to Swarm; changes "Automated Tests" icon
        if result:
            link = self.settings.pass_link
        else:
            link = self.settings.fail_link

        try:
            urllib.urlopen(link)
        except IOError as e:
            if e.args[0] == "http error":
                text = "HTTP error " + unicode(e.args[1]) + ": " + e.args[2]
            else:
                text = unicode(e)
            text += "\nPossible reasons of this error:" + \
                    "\n * Network errors" + \
                    "\n * Swarm parameters ('pass'/'fail' links) retrieved or parsed incorrectly"
            raise CiException(text)

        # Voting up or down; posting comments if any
        # An addition to "Automated Tests" functionality, requires login to Swarm
        self.get_swarm_session()
        self.session.vote_review(self.settings.review_id, result)
        if report_text:
            self.session.post_comment(self.settings.review_id, report_text)
