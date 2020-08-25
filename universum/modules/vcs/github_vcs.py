import datetime
import importlib
import urllib.parse

import requests

from ...lib.gravity import Dependency
from ...lib import utils
from ...lib.gravity import Module
from ..reporter import ReportObserver, Reporter
from . import git_vcs

__all__ = [
    "GithubToken",
    "GithubMainVcs"
]

github = None


def get_time():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class GithubToken(Module):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub", "GitHub repository settings")

        parser.add_argument("--github-app-id", "-gta", dest="integration_id", metavar="GITHUB_APP_ID",
                            help="GitHub application ID to use for check run report. Only GitHub App "
                                 "can report a check run result! If you don't have an App for reporting purposes, "
                                 "please don't use '--report-to-review' with GitHub")
        parser.add_argument("--github-private-key", "-gtk", dest="key", metavar="GITHUB_PRIVATE_KEY",
                            help="GitHub App private key for obtaining installation authentication token. "
                                 "Pass raw key data via environment variable, or redirect key reading to stdin "
                                 "by passing '-' as param value, or pass a file path to read the key from "
                                 "by starting the value string with '@'. File path can be either absolute or relative")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils.check_required_option(self.settings, "integration_id", """
                    GitHub App ID not specified.

                    Only GitHub Application owner knows this ID. If you are the App owner,
                    please check your App's general settings. If not, please contact the App owner
                    for this information.
                    
                    Please note that `universum github-handler` DOES NOT pass App ID to CI builds. 
                    Please specify the checkout id by using '--github-app-id' ('-gta')
                    command line parameter or by setting GITHUB_APP_ID environment variable.
                """)

        self.key = utils.read_and_check_multiline_option(self.settings, "key", """
                    GitHub App private key not specified.

                    As a multiline string, the private key is not very convenient to pass via command line directly.
                    Please store it in environment variable ("GITHUB_PRIVATE_KEY"), or enter through the stdin
                    (pass '-' param value for redirection), or pass a filename starting with '@' character, absolute or
                    relative starting from project root.

                    Please note that `universum github-handler` DOES NOT pass private key to CI builds.
                """)

        global github
        try:
            github = importlib.import_module("github")
        except ImportError as e:
            text = "Error: using GitHub Handler or VCS type 'github' requires Python package 'pygithub' " \
                   "to be installed to the system for correct GitHub App token processing. " \
                   "It also requires Python package 'cryptography' to be installed in addition. " \
                   "Please refer to `Prerequisites` chapter of project documentation for detailed instructions"
            raise ImportError(text) from e

        self.token_issued = None
        self._token = None

    def _get_token(self, installation_id):
        integration = github.GithubIntegration(self.settings.integration_id, self.key)
        auth_obj = integration.get_access_token(installation_id)
        return auth_obj.token

    def get_token(self, installation_id):
        if self._token:
            token_age = (datetime.datetime.now() - self.token_issued).total_seconds() / 60
            if token_age < 55:  # GitHub token lasts for one hour
                return self._token
        self._token = self._get_token(installation_id)
        self.token_issued = datetime.datetime.now()
        return self._token


class GithubTokenWithInstallation(GithubToken):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub", "GitHub repository settings")

        parser.add_argument("--github-installation-id", "-gti", dest="installation_id",
                            metavar="GITHUB_INSTALLATION_ID",
                            help="GitHub installation ID identifies specific app installation into user account "
                                 "or organization. Can be retrieved from web-hook or obtained via REST API; "
                                 "in standard workflow should be received from `universum github-handler`")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils.check_required_option(self.settings, "installation_id", """
                    GitHub App installation ID not specified.

                    An installation refers to any user or organization account that has installed the app.
                    Even if someone installs the app on more than one repository, it only counts as one
                    installation because it's within the same account.
                    Installation ID can be retrieved via REST API or simply parsed from GitHub App web-hook.
                    
                    If using `universum github-handler`, installation ID is passed automatically to 
                    GITHUB_INSTALLATION_ID environment variable.
                """)

    def get_token(self, installation_id=None):
        return super().get_token(installation_id=self.settings.installation_id)


class GithubMainVcs(ReportObserver, git_vcs.GitMainVcs, GithubTokenWithInstallation):
    """
    This class mostly contains functions for Gihub report observer
    """
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub", "GitHub repository settings")

        parser.add_argument("--github-check-name", "-ghc", dest="check_name", metavar="GITHUB_CHECK_NAME",
                            default="Universum check", help="The name of Github check run")
        parser.add_argument("--github-check-id", "-ghi", dest="check_id", metavar="GITHUB_CHECK_ID",
                            help="Github check run ID")
        parser.add_argument("--github-api-url", "-gha", dest="api_url", metavar="GITHUB_API_URL",
                            default="https://api.github.com/", help="API URL for integration")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reporter = None
        utils.check_required_option(self.settings, "checkout_id", """
                    git checkout id for github is not specified.

                    For github the git checkout id defines the commit to be checked and reported.
                    Please specify the checkout id by using '--git-checkout-id' ('-gco')
                    command line parameter or by setting GIT_CHECKOUT_ID environment variable.

                    In CI builds commit ID is usually extracted from webhook and handled automatically.
                """)

        utils.check_required_option(self.settings, "check_id", """
                    github check id is not specified.

                    GitHub check runs each have unique ID, that is used to update check result.
                    To integrate Universum with GitHub, check run should be already created before performing
                    actual check. Please specify check run ID by using '--github-check-id' ('-ghi')
                    command line parameter or by setting GITHUB_CHECK_ID environment variable.
                """)

        self.request = dict()
        self.request["status"] = "in_progress"
        self.request["output"] = {
            "title": self.settings.check_name,
            "summary": ""
        }

    def _clone(self, history_depth, destination_directory, clone_url):
        parsed_repo = urllib.parse.urlsplit(clone_url)
        if parsed_repo.scheme == "https" and not parsed_repo.username:
            new_netloc = "x-access-token:{}@{}".format(self.get_token(), parsed_repo.netloc)
            parsed_repo = (parsed_repo.scheme, new_netloc, parsed_repo.path, parsed_repo.query, parsed_repo.fragment)
        clone_url = urllib.parse.urlunsplit(parsed_repo)
        super()._clone(history_depth, destination_directory, clone_url)

    def code_review(self):
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self):
        self.out.log("GitHub has no review versions")

    def get_review_link(self):
        return self.settings.repo.rsplit(".git", 1)[0] + "/runs/" + self.settings.check_id

    def is_latest_version(self):  # pylint: disable=no-self-use
        return True

    def _report(self):
        repo_path = str(urllib.parse.urlsplit(self.settings.repo).path).rsplit(".git", 1)[0]
        check_url = self.settings.api_url + "repos" + repo_path + "/check-runs/" + self.settings.check_id

        headers = {
            "Accept": "application/vnd.github.antiope-preview+json",
            "Authorization": "token " + self.get_token()
        }

        utils.make_request(check_url, request_method="PATCH", json=self.request, headers=headers)

    def code_report_to_review(self, report):
        # git show returns string, each file separated by \n,
        # first line consists of commit id and commit comment, so it's skipped
        commit_files = self.repo.git.show("--name-only", "--oneline", self.settings.checkout_id).split('\n')[1:]
        comments = []
        for path, issues in report.items():
            if path in commit_files:
                for issue in issues:
                    comments.append(dict(path=path,
                                         message=issue['message'],
                                         start_line=issue['line'],
                                         end_line=issue['line'],
                                         annotation_level="warning"))
        self.request["output"]["annotations"] = comments
        self._report()

    def report_start(self, report_text):
        self.request["started_at"] = get_time()
        self.request["output"]["summary"] = report_text
        self._report()

    def report_result(self, result, report_text=None, no_vote=False):
        if result:
            conclusion = "success"
        else:
            conclusion = "failure"

        if not report_text:
            report_text = ""

        self.request["status"] = "completed"
        self.request["completed_at"] = get_time()
        self.request["conclusion"] = conclusion
        self.request["output"]["summary"] = report_text
        self._report()
