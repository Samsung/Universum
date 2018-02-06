# -*- coding: UTF-8 -*-

import json
import urlparse
import sh

from . import git_vcs, utils
from .ci_exception import CiException
from .gravity import Dependency
from .module_arguments import IncorrectParameterError
from .reporter import ReportObserver, Reporter

__all__ = [
    "GerritVcs"
]


class GerritVcs(ReportObserver, git_vcs.GitVcs):
    """
        This class contains encapsulates Gerrit VCS functions (not code review)
        """
    reporter_factory = Dependency(Reporter)

    @staticmethod
    def define_arguments(argument_parser, hide_sync_options=False):
        pass

    def __init__(self, project_root, report_to_review):
        self.super_init(GerritVcs, project_root, False)
        self.report_to_review = report_to_review

        if not self.settings.repo.startswith("ssh://"):
            raise IncorrectParameterError("Right now Gerrit builds are only available via SSH access")

        parsed_repo = urlparse.urlparse(self.settings.repo)
        self.hostname = parsed_repo.hostname
        self.ssh = sh.ssh.bake(parsed_repo.username+"@"+self.hostname, p=parsed_repo.port)
        self.commit_id = None

        if self.report_to_review:
            self.reporter = self.reporter_factory()
            self.reporter.subscribe(self)

    def get_review_link(self):
        refspec = self.settings.refspec
        if refspec.startswith("refs/"):
            refspec = refspec[5:]
        change = refspec.split("/")[2]
        return "https://" + self.hostname + "/#/c/" + change + "/"

    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        change = self.git_commit_locally(description, file_list, edit_only=edit_only)

        self.repo.remotes.origin.push(progress=self.logger, refspec="HEAD:refs/for/" + self.refspec)

        if not review:
            text = "gerrit review --submit --code-review +2 --label Verified=1 --message 'This is an automatic vote' "
            text += change
            self.run_ssh_command(text)

        return change

    def prepare_repository(self):
        super(GerritVcs, self).prepare_repository()
        self.commit_id = unicode(self.repo.head.commit)

        if self.report_to_review:
            self.out.log("Please see the link to the review:\n\n    " + self.get_review_link() + "\n")

    def run_ssh_command(self, line, stdin=None):
        try:
            self.ssh(line, _in=stdin)
        except sh.ErrorReturnCode as e:
            text = "Got exit code " + unicode(e.exit_code) + \
                   " while executing the following command:\n" + unicode(e.full_cmd)
            if e.stderr:
                text += utils.trim_and_convert_to_unicode(e.stderr) + "\n"
            raise CiException(text)

    def code_report_to_review(self, report):
        # git show returns string, each file separated by \n,
        # first line consists of commit id and commit comment, so it's skipped
        commit_files = self.repo.git.show("--name-only", "--oneline", self.commit_id).split('\n')[1:]
        for path, issues in report.iteritems():
            text = "gerrit review " + self.commit_id + ' --json '
            if path in commit_files:
                stdin = {'comments': {path: issues}}
                self.run_ssh_command(text, json.dumps(stdin))

    def report_start(self, report_text):
        text = "gerrit review --message '" + report_text + "' " + self.commit_id
        self.run_ssh_command(text)

    def report_result(self, result, report_text=None):
        if result:
            vote = "--label Verified=1 "
        else:
            vote = "--label Verified=-1 "

        text = "gerrit review " + vote
        if report_text:
            text += "--message '" + report_text + "' "

        text += self.commit_id
        self.run_ssh_command(text)
