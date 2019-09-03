# -*- coding: UTF-8 -*-

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

    def code_review(self):
        self.reporter = self.reporter_factory()
        self.reporter.subscribe(self)
        return self

    def update_review_version(self):
        self.out.log("GitHub has no review versions")

    def get_review_link(self):
        return self.settings.repo.split(".git")[0] + self.settings.checkout_id

    def is_latest_version(self):
        return True

    def code_report_to_review(self, report):
        pass

    def report_start(self, report_text):
        pass

    def report_result(self, result, report_text=None, no_vote=False):
        pass
