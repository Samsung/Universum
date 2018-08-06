# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import os

import git
import pytest

from . import utils


class GitServer(object):
    def __init__(self, working_directory, branch_name):
        self.url = "file://" + unicode(working_directory)
        self.target_branch = branch_name
        self.target_file = "readme.txt"

        self._working_directory = working_directory
        self._repo = git.Repo.init(unicode(working_directory))
        configurator = self._repo.config_writer()
        configurator.set_value("user", "name", "Testing user")
        configurator.set_value("user", "email", "some@email.com")
        self._file = self._working_directory.join(self.target_file)
        self._file.write("")

        self._repo.index.add([unicode(self._file)])
        self._repo.index.commit("initial commit")
        self._commit_count = 0

        self._branch = self._repo.create_head(branch_name)

    def make_a_change(self):
        self._branch.checkout()

        self._file.write("One more line\n")
        self._commit_count += 1

        self._repo.index.add([unicode(self._file)])
        change = unicode(self._repo.index.commit("add line " + unicode(self._commit_count)))
        self._repo.heads.master.checkout()
        return change

    def commit_new_file(self):
        """ Make a mergeble commit """
        self._commit_count += 1
        test_file = self._working_directory.join("test%s.txt" % self._commit_count)
        test_file.write("Commit number #%s" % (self._commit_count))
        self._repo.index.add([unicode(test_file)])
        return unicode(self._repo.index.commit("Add file " + unicode(self._commit_count)))

    def make_branch(self, name):
        self._repo.git.checkout("-b", name)

    def switch_branch(self, name):
        self._repo.git.checkout(name)

    def merge_branch(self, name, fast_forward):
        """
        Merge specified branch to the current
        :param name: Name of merged branch
        :param fast_forward: Boolean. Try to use fast forward or create a merge commit on merge
        :return: None
        """
        if fast_forward:
            cmd_option = "--ff-only"
        else:
            cmd_option = "--no-ff"
        self._repo.git.merge(cmd_option, name)

    def get_last_commit(self):
        return self._repo.git.log('-n1', pretty='format:"%H"').replace('"', '')


@pytest.fixture()
def git_server(tmpdir):
    directory = tmpdir.mkdir("server")
    yield GitServer(directory, "testing")


class GitEnvironment(utils.TestEnvironment):
    def __init__(self, server, directory, test_type):
        db_file = directory.join("gitpoll.json")
        self.db_file = unicode(db_file)
        self.root_directory = directory.mkdir("client")

        super(GitEnvironment, self).__init__(test_type)

        self.server = server
        self.repo = git.Repo.clone_from(self.server.url, unicode(self.root_directory))
        self.repo.git.checkout(self.server.target_branch)
        self.repo_file = self.root_directory.join(self.server.target_file)

        self.settings.Vcs.type = "git"
        self.settings.GitVcs.repo = server.url
        self.settings.GitVcs.refspec = server.target_branch
        self.settings.GitVcs.user = "Testing User"
        self.settings.GitVcs.email = "some@email.com"

    def get_last_change(self):
        changes = self.repo.git.log("origin/" + self.server.target_branch, pretty="oneline", max_count=1)
        return changes.split(" ")[0]

    def file_present(self, file_path):
        relative_path = os.path.relpath(file_path, unicode(self.root_directory))
        return relative_path in self.repo.git.ls_files(file_path)

    def text_in_file(self, text, file_path):
        relative_path = os.path.relpath(file_path, unicode(self.root_directory))
        return text in self.repo.git.show("HEAD:" + relative_path)

    def make_a_change(self):
        return self.server.make_a_change()
