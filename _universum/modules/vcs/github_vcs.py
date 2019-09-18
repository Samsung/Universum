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


def get_time():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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
        parser.add_argument("--github-check-id", "-ghi", dest="check_id", metavar="GITHUB_CHECK_ID",
                            help="Github check run ID")
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
        utils.check_required_option(self.settings, "token", """
                    github api token is not specified.

                    GitHub API token is used for application authorization. Expected format is
                    'v1.4e96f8c2d1922c3b154a65ca7ecb91f6994fb0c5'.
                    Please specify the token by using '--github-token' ('-ght')
                    command line parameter or by setting GITHUB_TOKEN environment variable.

                    In CI builds github api token is expected to be acquired automatically before build.
                    For information on how to acquire the token please see
                    https://developer.github.com/v3/oauth_authorizations/
                """)
        utils.check_required_option(self.settings, "check_id", """
                    github check id is not specified.

                    GitHub check runs each have unique ID, that is used to update check result.
                    To integrate Universum with GitHub, check run should be already created before performing
                    actual check. Please specify check run ID by using '--github-check-id' ('-ghi')
                    command line parameter or by setting GITHUB_CHECK_ID environment variable.
                """)

        parsed_repo = urlparse.urlsplit(self.settings.repo)
        repo_path = unicode(parsed_repo.path).rsplit(".git", 1)[0]
        self.check_url = self.settings.api_url + "repos" + repo_path + "/check-runs/" + self.settings.check_id
        if parsed_repo.scheme == "https" and not parsed_repo.username:
            new_netloc = "x-access-token:{}@{}".format(self.settings.token, parsed_repo.netloc)
            parsed_repo = (parsed_repo.scheme, new_netloc, parsed_repo.path, parsed_repo.query, parsed_repo.fragment)
        self.clone_url = urlparse.urlunsplit(parsed_repo)
        self.headers = {
            "Accept": "application/vnd.github.antiope-preview+json",
            "Authorization": "token " + self.settings.token
        }

    def code_review(self):
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self):
        self.out.log("GitHub has no review versions")

    def get_review_link(self):
        return self.settings.repo.rsplit(".git", 1)[0] + "/runs/" + self.settings.check_id

    def is_latest_version(self):
        return True

    def code_report_to_review(self, report):
        # git show returns string, each file separated by \n,
        # first line consists of commit id and commit comment, so it's skipped
        commit_files = self.repo.git.show("--name-only", "--oneline", self.commit_id).split('\n')[1:]
        comments = []
        for path, issues in report.iteritems():
            if path in commit_files:
                for issue in issues:
                    comments.append(dict(path=path,
                                         message=issue['message'],
                                         start_line=issue['line'],
                                         end_line=issue['line'],
                                         annotation_level="warning"))
        request = {
            "output": {
                "annotations": comments
            }
        }

        result = requests.patch(self.check_url, json=request, headers=self.headers)
        utils.check_request_result(result)

    def report_start(self, report_text):
        request = {
            "status": "in_progress",
            "started_at": get_time(),
            "output": {
                "title": self.settings.check_name,
                "summary": report_text
            }
        }

        result = requests.patch(self.check_url, json=request, headers=self.headers)
        utils.check_request_result(result)

    def report_result(self, result, report_text=None, no_vote=False):
        if result:
            conclusion = "success"
        else:
            conclusion = "failure"

        if not report_text:
            report_text = ""

        request = {
            "status": "completed",
            "completed_at":  get_time(),
            "conclusion": conclusion,
            "output": {
                "title": self.settings.check_name,
                "summary": report_text
            }
        }

        result = requests.patch(self.check_url, json=request, headers=self.headers)
        utils.check_request_result(result)
