import json
import urllib.parse
from typing import Dict, List, Union, Optional
from typing_extensions import Self

from . import git_vcs
from ..reporter import ReportObserver, Reporter
from ...lib import utils
from ...lib.gravity import Dependency
from ...lib.module_arguments import ModuleArgumentParser

__all__ = [
    "GithubActionsMainVcs"
]


class GithubActionsMainVcs(ReportObserver, git_vcs.GitMainVcs):
    """
    This class mostly contains functions for GitHub report observer
    """
    reporter_factory: Dependency = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser: ModuleArgumentParser) -> None:
        parser: ModuleArgumentParser = argument_parser.get_or_create_group("GitHub Actions",
                                                                           "GitHub repository settings for GH Actions")

        parser.add_argument("--ghactions-token", "-ght", dest="token", metavar="GITHUB_TOKEN",
                            help="Is stored in ${{ secrets.GITHUB_TOKEN }}")
        parser.add_argument("--ghactions-payload", "-ghp", dest="payload", metavar="GITHUB_PAYLOAD",
                            help="File path: ${{ github.event_path }}")

    def __init__(self, *args, **kwargs) -> None:
        self.settings.repo = "Will be filled after payload parsing"
        super().__init__(*args, **kwargs)
        self.reporter: Reporter = None  # type: ignore

        self.check_required_option("token", """
            The GitHub workflow token is not specified.

            Token is automatically created by GitHub Actions and stored in 
            ${{ secrets.GITHUB_TOKEN }} environment variable. For Universum
            to work correctly please copy it to ${{ env.GITHUB_TOKEN }}
            (as due to security reasons Universum cannot get access to secrets directly),
            or pass it directly using '--ghactions-token' ('-ght') command line parameter.
            """)

        self.payload: str = self.read_and_check_multiline_option("payload", """
            GitHub web-hook payload JSON is not specified.

            Please pass the payload stored in ${{ github.event_path }} file to this parameter
            directly via '--ghactions-payload' ('-ghp') command line parameter or by setting
            GITHUB_PAYLOAD environment variable, or by passing file path as the argument value
            (start filename with '@' character, e.g. '@/tmp/file.json' or '@payload.json' for
            relative path starting at current directory). Please note, that when passing
            a file, it's expected to be in UTF-8 encoding.
            """)

        try:
            self.payload_json: dict = json.loads(self.payload)
            self.settings.repo = self.payload_json['repository']['html_url']
            self.settings.refspec = self.payload_json['pull_request']['head']['ref']
        except json.decoder.JSONDecodeError as error:
            self.error(f"Provided payload value could not been parsed as JSON "
                       f"and returned the following error:\n {error}")

    def _clone(self, history_depth: int, destination_directory: str, clone_url: str) -> None:
        parsed_repo: urllib.parse.SplitResult = urllib.parse.urlsplit(clone_url)
        if parsed_repo.scheme == "https" and not parsed_repo.username:
            new_netloc = f"{self.settings.token}@{parsed_repo.netloc}"
            parsed_repo = (parsed_repo.scheme, new_netloc, parsed_repo.path,
                           parsed_repo.query, parsed_repo.fragment)  # type: ignore
        clone_url = str(urllib.parse.urlunsplit(parsed_repo))
        super()._clone(history_depth, destination_directory, clone_url)

    def code_review(self) -> Self:
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self) -> None:
        self.out.log("GitHub has no review versions")

    def get_review_link(self) -> str:
        return self.payload_json['pull_request']['html_url']

    def is_latest_version(self) -> bool:
        return True

    def _report(self, url, request: dict) -> None:
        headers: Dict = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer { self.settings.token }"
        }

        utils.make_request(url, request_method="POST", json=request, headers=headers, timeout=5*60)

    def code_report_to_review(self, report: dict) -> None:
        # git show returns string, each file separated by \n,
        # first line consists of commit id and commit comment, so it's skipped
        commit_files: List[str] = self.repo.git.show("--name-only", "--oneline",
                                                     self.settings.checkout_id).split('\n')[1:]
        # NB! When using GITHUB_TOKEN, the rate limit is 1,000 requests per hour per repository.
        # (https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28  ->
        #                                              #rate-limits-for-requests-from-github-actions)
        # Therefore the following reporting cycle will FAIL if PR has more than 1,000 analyzer issues
        for path, issues in report.items():
            if path not in commit_files:
                continue
            for issue in issues:
                request = dict(path=path,
                               commit_id=self.payload_json['pull_request']['head']['sha'],
                               body=issue['message'],
                               line=issue['line'],
                               side="RIGHT")
                self._report(self.payload_json['pull_request']['review_comments_url'], request)

    def report_start(self, report_text: str) -> None:
        pass

    def report_result(self, result: bool, report_text: Optional[str] = None, no_vote: bool = False):
        if not report_text:
            report_text = "Universum check finished"
        self._report(self.payload_json['pull_request']['comments_url'], {"body": report_text})
