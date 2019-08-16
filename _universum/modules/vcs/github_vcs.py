# -*- coding: UTF-8 -*-

from ...lib.gravity import Dependency
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
        parser = argument_parser.get_or_create_group("Git", "Git repository settings")

        parser.add_argument("--github-token", "-ght", dest="token", metavar="GITHUB_TOKEN",
                            help="GitHub API token; for details see "
                                 "https://developer.github.com/v3/oauth_authorizations/")
        parser.add_argument("--github-check-name", "-ghc", dest="check_name", metavar="GITHUB_CHECK_NAME",
                            help="The name of Github check run")

    def __init__(self, *args, **kwargs):
        super(GithubMainVcs, self).__init__(*args, **kwargs)
        self.reporter = None

    def code_review(self):
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self):
        self.out.log("GitHub has no review versions")

    def get_review_link(self):
        return self.settings.repo.split(".git") + self.settings.checkout_id

    def is_latest_version(self):
        return True

    def code_report_to_review(self, report):
        pass

    def report_start(self, report_text):
        pass

    def report_result(self, result, report_text=None, no_vote=False):
        pass

    def prepare_repository(self):
        pass