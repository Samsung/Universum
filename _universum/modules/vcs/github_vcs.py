# -*- coding: UTF-8 -*-

import datetime
import requests
import urlparse

from ...lib.gravity import Dependency
from ...lib import utils
from ..reporter import ReportObserver, Reporter
from . import git_vcs

__all__ = [
    "GithubMainVcs"
]


class GithubMainVcs(ReportObserver, git_vcs.GitMainVcs):
    """
    This class mostly contains functions for Gihub report observer
    """
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub", "GitHub repository settings")

        parser.add_argument("--github-token", "-ght", dest="token", metavar="GITHUB_TOKEN",
                            help="GitHub API token; for details see "
                                 "https://developer.github.com/v3/oauth_authorizations/")
        parser.add_argument("--github-check-name", "-ghc", dest="check_name", metavar="GITHUB_CHECK_NAME",
                            default="Universum check", help="The name of Github check run")
        parser.add_argument("--github-api-url", "-gha", dest="api_url", metavar="GITHUB_API_URL",
                            default="https://api.github.com/", help="API URL for integration")

    def __init__(self, *args, **kwargs):
        super(GithubMainVcs, self).__init__(*args, **kwargs)
        self.reporter = None
        utils.check_required_option(self.settings, "checkout_id", """
                    git checkout id for github is not specified.

                    For github the git checkout id defines the commit to be checked and reported.
                    Please specify the checkout id by using '--git-checkout-id' ('-gco')
                    command line parameter or by setting GIT_CHECKOUT_ID environment variable.

                    In CI builds commit ID is usually extracted from webhook and handled automatically.  
                """)

        parsed_repo = urlparse.urlparse(self.settings.repo)
        self.repo_path = unicode(parsed_repo.path).strip(".git")

    def code_review(self):
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self):
        self.out.log("GitHub has no review versions")

    def get_review_link(self):
        return self.settings.repo.split(".git")[0] + "/" + self.settings.checkout_id

    def is_latest_version(self):
        return True

    def code_report_to_review(self, report):
        pass

    def report_start(self, report_text):
        headers = {
            "Accept": "application/vnd.github.antiope-preview+json",
            "Authorization": "token " + self.settings.token
        }
        request = {
            "name": self.settings.check_name,
            "status": "in_progress",
            "started_at": datetime.datetime.now().isoformat(),
            "output": {
                "title": self.settings.check_name,
                "summary": report_text
            }
        }

        path = self.settings.api_url + "repos" + self.repo_path + "/check-runs"
        result = requests.post(path, data=request, headers=headers)
        utils.check_request_result(result)

    def report_result(self, result, report_text=None, no_vote=False):
        headers = {
            "Accept": "application/vnd.github.antiope-preview+json",
            "Authorization": "token " + self.settings.token
        }
        if result:
            conclusion = "success"
        else:
            conclusion = "failure"

        if not report_text:
            report_text = ""

        request = {
            "name": self.settings.check_name,
            "status": "completed",
            "completed_at": datetime.datetime.now().isoformat(),
            "conclusion": conclusion,
            "output": {
                "title": self.settings.check_name,
                "summary": report_text
            }
        }

        path = self.settings.api_url + "repos" + self.repo_path + "/check-runs"
        result = requests.post(path, data=request, headers=headers)
        utils.check_request_result(result)
