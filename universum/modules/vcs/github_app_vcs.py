import datetime
import importlib
import urllib.parse

from . import git_vcs
from ..error_state import HasErrorState
from ..reporter import ReportObserver, Reporter
from ...lib import utils
from ...lib.gravity import Dependency

__all__ = [
    "GithubToken",
    "GithubAppMainVcs"
]

github = None


def get_time():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class GithubToken(HasErrorState):

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub App", "GitHub repository settings for application")

        parser.add_argument("--ghapp-app-id", "-gta", dest="integration_id", metavar="GITHUB_APP_ID",
                            help="GitHub application ID to use for check run report. Only GitHub App "
                                 "can report a check run result! If you don't have an App for reporting purposes, "
                                 "please don't use ``--report-to-review`` with GitHub")
        parser.add_argument("--ghapp-private-key", "-gtk", dest="key", metavar="GITHUB_PRIVATE_KEY",
                            help="GitHub App private key for obtaining installation authentication token. "
                                 "Pass raw key data via environment variable or pass a file path to read the key from "
                                 "by starting the value string with '@'. File path can be either absolute or relative. "
                                 "Please note, that when passing a file, it is expected to be in UTF-8 encoding")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_required_option("integration_id", """
            The GitHub App ID is not specified.

            Only GitHub Application owner knows this ID. If you are the App owner, please
            check your App's general settings. If not, please contact the App owner for this
            information.

            Please note that 'universum github-handler' DOES NOT pass App ID to CI builds.
            It is assumed that one CI configuration (job, build, workflow) serves as one
            GitHub App. Because of that, it is required to specify App ID within the CI
            configuration.

            Please specify the GitHub App ID by using '--github-app-id' ('-gta') command
            line parameter or by setting GITHUB_APP_ID environment variable.
            """)

        self.key = self.read_and_check_multiline_option("key", """
            The GitHub App private key is not specified.

            Please note that 'universum github-handler' DOES NOT pass private key to CI
            builds. It is assumed that one CI configuration (job, build, workflow) serves as
            one GitHub App. Because of that, it is required to specify private key within
            the CI configuration.

            As the private key is a multiline string, it is not convenient to pass it
            directly via command line. If you start the parameter with '@', the rest should be
            the path to a file containing the key. The path can be absolute or relative to the 
            project root. You can also store the key in GITHUB_PRIVATE_KEY environment variable.
            Please note, that when passing a file, it's expected to be in UTF-8 encoding")
            """)

        global github
        try:
            github = importlib.import_module("github")
        except ImportError as e:
            text = "Error: using GitHub Handler or VCS type 'github' requires Python package 'pygithub' " \
                   "to be installed to the system for correct GitHub App token processing. " \
                   "It also requires Python package 'cryptography' to be installed in addition. " \
                   "Please refer to 'Prerequisites' chapter of project documentation for detailed instructions"
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
        parser = argument_parser.get_or_create_group("GitHub App", "GitHub repository settings for application")

        parser.add_argument("--ghapp-installation-id", "-gti", dest="installation_id",
                            metavar="GITHUB_INSTALLATION_ID",
                            help="GitHub installation ID identifies specific app installation into user account "
                                 "or organization. Can be retrieved from web-hook or obtained via REST API; "
                                 "in standard workflow should be received from 'universum github-handler'")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_required_option("installation_id", """
            The GitHub App installation ID not specified.

            An installation refers to any user or organization account that has installed
            the app. Even if someone installs the app on more than one repository, it only
            counts as one installation because it's within the same account. Installation ID
            can be retrieved via REST API or simply parsed from GitHub App web-hook.

            If using 'universum github-handler', installation ID is automatically extracted
            from the webhook payload and  passed via GITHUB_INSTALLATION_ID environment
            variable.
            """)

    def get_token(self, installation_id=None):
        return super().get_token(installation_id=self.settings.installation_id)


class GithubAppMainVcs(ReportObserver, git_vcs.GitMainVcs, GithubTokenWithInstallation):
    """
    This class mostly contains functions for GitHub report observer
    """
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("GitHub App", "GitHub repository settings for application")

        parser.add_argument("--ghapp-check-name", "-ghc", dest="check_name", metavar="GITHUB_CHECK_NAME",
                            default="Universum check", help="The name of Github check run")
        parser.add_argument("--gapp-check-id", "-ghi", dest="check_id", metavar="GITHUB_CHECK_ID",
                            help="Github check run ID")
        parser.add_argument("--ghapp-api-url", "-gha", dest="api_url", metavar="GITHUB_API_URL",
                            default="https://api.github.com/", help="API URL for integration")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reporter = None

        self.check_required_option("checkout_id", """
            The git checkout id for github is not specified.

            For github the git checkout id defines the commit to be checked and reported.
            Please specify the checkout id by using '--git-checkout-id' ('-gco') command
            line parameter or by setting GIT_CHECKOUT_ID environment variable.

            If using 'universum github-handler', the checkout ID is automatically extracted
            from the webhook payload and passed via GIT_CHECKOUT_ID environment variable.
            """)

        self.check_required_option("check_id", """
            The GitHub Check Run ID is not specified.

            GitHub check runs each have unique ID, that is used to update check result. To
            integrate Universum with GitHub, check run should be already created before
            performing actual check. Please specify check run ID by using
            '--github-check-id' ('-ghi') command line parameter or by setting
            GITHUB_CHECK_ID environment variable.

            If using 'universum github-handler', the check ID is automatically extracted
            from the webhook payload and passed via GITHUB_CHECK_ID environment variable.
            """)

        self.request = {}
        self.request["status"] = "in_progress"
        self.request["output"] = {
            "title": self.settings.check_name,
            "summary": ""
        }

    def _clone(self, history_depth, destination_directory, clone_url):
        parsed_repo = urllib.parse.urlsplit(clone_url)
        if parsed_repo.scheme == "https" and not parsed_repo.username:
            new_netloc = f"x-access-token:{self.get_token()}@{parsed_repo.netloc}"
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

    def is_latest_version(self):
        return True

    def _report(self):
        repo_path = str(urllib.parse.urlsplit(self.settings.repo).path).rsplit(".git", 1)[0]
        check_url = self.settings.api_url + "repos" + repo_path + "/check-runs/" + self.settings.check_id

        headers = {
            "Accept": "application/vnd.github.antiope-preview+json",
            "Authorization": "token " + self.get_token()
        }

        utils.make_request(check_url, request_method="PATCH", json=self.request, headers=headers, timeout=5*60)

    def code_report_to_review(self, report):
        # git show returns string, each file separated by \n,
        # first line consists of commit id and commit comment, so it's skipped
        commit_files = self.repo.git.show("--name-only", "--oneline", self.settings.checkout_id).split('\n')[1:]
        comments = []
        for path, issues in report.items():
            if path not in commit_files:
                continue
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
