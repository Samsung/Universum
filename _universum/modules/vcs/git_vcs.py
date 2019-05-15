# -*- coding: UTF-8 -*-

import glob
import os

from .base_vcs import BaseVcs, BaseDownloadVcs
from ..output import needs_output
from ..structure_handler import needs_structure
from ...lib import utils
from ...lib.ci_exception import CriticalCiException
from ...lib.module_arguments import IncorrectParameterError
from ...lib.utils import make_block, convert_to_str

__all__ = [
    "GitMainVcs",
    "GitSubmitVcs",
    "GitPollVcs"
]

git = None


def catch_git_exception(ignore_if=None):
    return utils.catch_exception("GitCommandError", ignore_if)


@needs_output
@needs_structure
class GitVcs(BaseVcs):
    """
    This class contains CI functions for interaction with Git
    """

    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Git", "Git repository settings")

        parser.add_argument("--git-repo", "-gr", dest="repo", metavar="GIT_REPO",
                            help="See your project home page for exact repository identifier, passed to 'git clone'. "
                                 "If using SSH, '--git-repo' format is 'ssh://user@server:port/detailed/path'")
        parser.add_argument("--git-refspec", "-grs", dest="refspec", metavar="GIT_REFSPEC",
                            help="Any additional refspec to be fetched")

    def __init__(self, *args, **kwargs):
        super(GitVcs, self).__init__(*args, **kwargs)

        global git
        try:
            git = utils.import_module("git")
            remote = utils.import_module("remote", target_name="git.remote", path=git.__path__)
        except ImportError:
            text = "Error: using VCS type 'git' requires official Git CLI and Python package 'gitpython' " \
                   "to be installed to the system. Please refer to `Prerequisites` chapter of project " \
                   "documentation for detailed instructions"
            raise ImportError(text)

        utils.check_required_option(self.settings, "repo", """
            the git repo is not specified.

            The repo defines the location of project source codes.
            Please specify the git repo by using '--git-repo' ('-gr') 
            command line parameter or by setting GIT_REPO environment
            variable.""")

        class Progress(remote.RemoteProgress):
            def __init__(self, out, *args, **kwargs):
                super(Progress, self).__init__(*args, **kwargs)
                self.out = out

            def line_dropped(self, line):
                self.out.log(line)

        self.repo = None
        self.logger = Progress(self.out)

        if getattr(self.settings, "refspec", None):
            if self.settings.refspec.startswith("origin/"):
                self.refspec = self.settings.refspec[7:]
            else:
                self.refspec = self.settings.refspec
        else:
            self.refspec = None

    @make_block("Cloning repository")
    @catch_git_exception()
    def clone_and_fetch(self, history_depth=None):
        self.out.log("Cloning '" + self.settings.repo + "'...")
        destination_directory = convert_to_str(self.settings.project_root)
        if history_depth:
            self.repo = git.Repo.clone_from(self.settings.repo, destination_directory,
                                            depth=history_depth, no_single_branch=True, progress=self.logger)
        else:
            self.repo = git.Repo.clone_from(self.settings.repo, destination_directory, progress=self.logger)

        self.sources_need_cleaning = True
        self.append_repo_status("Git repo: " + self.settings.repo + "\n\n")

        self.out.log("Please note that default remote name is 'origin'")
        if self.settings.refspec:
            self.repo.remotes.origin.fetch(refspec=self.settings.refspec, progress=self.logger)
            self.append_repo_status("Fetched refspec: " + self.settings.refspec + "\n")


@needs_output
@needs_structure
class GitMainVcs(GitVcs, BaseDownloadVcs):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Git")

        parser.add_argument("--git-checkout-id", "-gco", dest="checkout_id", metavar="GIT_CHECKOUT_ID",
                            help="A commit ID to checkout. "
                                 "Could be exact commit hash, or branch name, or tag, etc.")

        parser.add_argument("--git-cherry-pick-id", "-gcp", action="append", nargs='+',
                            metavar="GIT_CHERRYPICK_ID", dest="cherrypick_id",
                            help="List of commit IDs to be cherry-picked, separated by comma. "
                                 "'--git-cherry-pick-id' can be added to the command line several times")

    def __init__(self, *args, **kwargs):
        super(GitMainVcs, self).__init__(*args, **kwargs)
        self.checkout_id = None

    @make_block("Checking out")
    @catch_git_exception()
    def check_out(self):
        if self.settings.checkout_id:
            self.checkout_id = self.settings.checkout_id
        elif self.settings.refspec:
            self.checkout_id = "FETCH_HEAD"
        else:
            self.checkout_id = "HEAD"
        self.out.log("Checking out '" + self.checkout_id + "'...")
        self.repo.git.checkout(self.checkout_id)
        self.append_repo_status("Checked out: " + self.checkout_id + "\n")

    @make_block("Cherry-picking")
    @catch_git_exception()
    def cherry_pick(self):
        cherrypick_id_list = sorted(list(set(utils.unify_argument_list(self.settings.cherrypick_id))))
        self.append_repo_status("Cherry-picked commits:")
        for commit in cherrypick_id_list:
            self.out.log("Cherry-picking '" + commit + "'...")
            self.repo.git.cherry_pick(commit, "--no-commit")
            self.append_repo_status(" " + commit)
        self.append_repo_status("\n")

    def _diff_against_reference_commit(self, commit_id):
        status_mapping = {
            'A': "add",
            'C': "copy",
            'D': "delete",
            'M': "modify",
            'R': "rename",
            'T': "change file type",
            'U': "unmerged",
            'X': "unknown"
        }
        result = []
        for line in self.repo.git.diff(commit_id, name_status=True).splitlines():
            try:
                diff_record = line.split()
                try:
                    # Some status letters are followed by score, e.g. 'R86'
                    status = status_mapping[diff_record[0][0]]
                except KeyError:
                    status = diff_record[0]

                result.append({"action": status,
                               "repo_path": diff_record[1],
                               "local_path": utils.parse_path(diff_record[-1], self.settings.project_root)})
            except IndexError:
                self.out.log_stderr(line)

        return result

    def calculate_file_diff(self):
        return self._diff_against_reference_commit(self.checkout_id)

    @catch_git_exception()
    def prepare_repository(self):
        self.clone_and_fetch()
        self.check_out()
        if self.settings.cherrypick_id:
            self.cherry_pick()

    def copy_cl_files_and_revert(self):
        raise NotImplementedError


@needs_output
class GitSubmitVcs(GitVcs):
    @staticmethod
    def define_arguments(argument_parser):
        parser = argument_parser.get_or_create_group("Git")

        parser.add_argument("--git-user", "-gu", dest="user", metavar="GITUSER",
                            help="Git user name for submitting")
        parser.add_argument("--git-email", "-ge", dest="email", metavar="GITEMAIL",
                            help="Git user email for submitting")

    def __init__(self, *args, **kwargs):
        super(GitSubmitVcs, self).__init__(*args, **kwargs)

        if not getattr(self.settings, "user", None) or not getattr(self.settings, "email", None):
            raise IncorrectParameterError("user name or email is not specified. \n\n"
                                          "Submitting changes to repository requires setting user name and email.\n"
                                          "Please use '--git-user' (GITUSER) and '--git-email' (GITEMAIL) parameters.")

    def get_list_of_modified(self, file_list):
        """
        Output of 'git status --porcelain' for most cases looks as following:

             M path/file.name
            ?? path/newly/created.file
             D path/deleted.file
            R  old/path/file -> new/path/file

        And for '--edit-only' submit option we should filter the 'M' records
        :param file_list: full list of vcs and directories to be reconciled
        :return: list of corresponding modified vcs
        """
        result = []
        all_changes = self.repo.git.status(porcelain=True).splitlines()

        modified_files = set()
        for file_record in all_changes:
            record_parameters = file_record.split(" ")
            if record_parameters[-2] == "M":
                full_path = utils.parse_path(record_parameters[-1], self.settings.project_root)
                modified_files.add(full_path)

        for file_path in file_list:
            all_matches = glob.glob(file_path)
            relative_path = os.path.relpath(file_path, self.settings.project_root)
            if not all_matches:
                self.out.log("Skipping '{}'...".format(relative_path))
                continue

            for matching_path in all_matches:
                relative_path = os.path.relpath(matching_path, self.settings.project_root)
                if os.path.isdir(matching_path):
                    files_in_dir = [os.path.relpath(item, self.settings.project_root)
                                    for item in modified_files if item.startswith(file_path)]
                    if not files_in_dir:
                        self.out.log("Skipping '{}'...".format(relative_path))
                    result.extend(files_in_dir)
                else:
                    if matching_path in modified_files:
                        result.append(relative_path)
                    else:
                        self.out.log("Skipping '{}'...".format(relative_path))
        return result

    def git_commit_locally(self, description, file_list, edit_only=False):
        try:
            self.repo = git.Repo(convert_to_str(self.settings.project_root))
        except git.exc.NoSuchPathError:
            raise CriticalCiException("No such directory as '" + self.settings.project_root + "'")
        except git.exc.InvalidGitRepositoryError:
            raise CriticalCiException("'" + self.settings.project_root + "' does not contain a Git repository")

        configurator = self.repo.config_writer()
        configurator.set_value("user", "name", self.settings.user)
        configurator.set_value("user", "email", self.settings.email)

        file_list = [utils.parse_path(item, self.settings.project_root) for item in file_list]
        relative_path_list = [os.path.relpath(item, self.settings.project_root) for item in file_list]

        if edit_only:
            self.repo.git.add(self.get_list_of_modified(file_list))
        else:
            self.repo.git.add(relative_path_list, all=True)

        repo_status = self.repo.git.status()
        nothing_committed = ("nothing added to commit" in repo_status or
                             "no changes added to commit" in repo_status or
                             "nothing to commit" in repo_status)
        if nothing_committed:
            return 0

        self.out.log(self.repo.git.commit(m=description))
        commit_id = unicode(self.repo.head.commit)
        self.out.log("Full commit ID is " + commit_id)
        return commit_id

    def submit_new_change(self, description, file_list, review=False, edit_only=False):
        change = self.git_commit_locally(description, file_list, edit_only=edit_only)
        if change == 0:
            return 0

        if review:
            raise CriticalCiException("'review' commits to non-gerrit Git are not supported at the moment. "
                                      "Specify temp branch for deletable commit manually if needed")

        self.repo.remotes.origin.push(progress=self.logger)
        return change


class GitPollVcs(GitVcs):
    def get_changes(self, changes_reference=None, max_number='1'):
        self.clone_and_fetch()
        if not changes_reference:
            changes_reference = {}
        result = {}

        branch_name = self.refspec
        result[branch_name] = []

        last_change = self.repo.git.log("origin/" + branch_name, pretty="oneline", max_count=1).split(" ")[0]
        reference_change = changes_reference.get(branch_name, last_change)

        # Ranges like "commit^.." do not work for single-commit branches, so reference change is processed manually
        result[branch_name].append(reference_change)
        submitted_changes = self.repo.git.log("--first-parent", "origin/" + branch_name, reference_change + "..",
                                              pretty="oneline", max_count=max_number).splitlines()

        submitted_changes.reverse()
        for change in submitted_changes:
            result[branch_name].append(change.split(" ")[0])

        return result
