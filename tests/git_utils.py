# pylint: disable = redefined-outer-name

import os
from time import sleep

import git
from git.remote import RemoteProgress
import pytest
import sh

from . import utils


class GitServer:
    def __init__(self, working_directory, branch_name):
        self.target_branch = branch_name
        self.target_file = "readme.txt"

        self._working_directory = working_directory
        self._repo = git.Repo.init(working_directory)
        self._repo.daemon_export = True
        self._daemon_started = False

        def std_redirect(line):
            print("[git daemon] " + line)
            if "Ready to rumble" in line:
                self._daemon_started = True

        port = utils.get_open_port()
        # We use this URL for now while docker works in 'host' mode
        # In 'host' mode host localhost is container localhost
        self.url = f"git://127.0.0.1:{port}{working_directory}"

        # pylint: disable = unexpected-keyword-arg, too-many-function-args
        # module sh built-in alias for sh.Command('git') causes pylint warnings
        self._daemon = sh.git("daemon", "--verbose", "--listen=127.0.0.1", f"--port={port}",
                              "--enable=receive-pack", str(working_directory),
                              _iter=True, _bg_exc=False, _bg=True,
                              _out=std_redirect, _err=std_redirect)

        with self._repo.config_writer() as configurator:
            configurator.set_value("user", "name", "Testing user")
            configurator.set_value("user", "email", "some@email.com")
        self._file = self._working_directory.join(self.target_file)
        self._file.write("")

        self._repo.index.add([str(self._file)])
        self._repo.index.commit("initial commit")
        self._commit_count = 0

        self._branch = self._repo.create_head(branch_name)

        while not self._daemon_started:
            sleep(1)

    def make_a_change(self):
        self._branch.checkout()

        self._file.write("One more line\n")
        self._commit_count += 1

        self._repo.index.add([str(self._file)])
        change = str(self._repo.index.commit(f"add line {self._commit_count}"))
        self._repo.heads.master.checkout()
        return change

    def commit_new_file(self):
        """ Make a mergeble commit """
        self._commit_count += 1
        test_file = self._working_directory.join(f"test{self._commit_count}.txt")
        test_file.write(f"Commit number #{self._commit_count}")
        self._repo.index.add([str(test_file)])
        return str(self._repo.index.commit(f"Add file {self._commit_count}"))

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

    def exit(self):
        try:
            self._daemon.terminate()
            self._daemon.wait()
        except sh.SignalException_SIGTERM:
            pass


@pytest.fixture()
def git_server(tmpdir):
    directory = tmpdir.mkdir("server")
    server = GitServer(directory, "testing")
    try:
        yield server
    finally:
        server.exit()


class GitClient(utils.BaseVcsClient):
    def __init__(self, git_server, directory):
        super().__init__()

        class Progress(RemoteProgress):
            def line_dropped(self, line):
                print(line)

        self.server = git_server
        self.logger = Progress()
        self.root_directory = directory.mkdir("client")
        self.repo = git.Repo.clone_from(git_server.url, self.root_directory)
        self.repo_file = self.root_directory.join(git_server.target_file)

    def get_last_change(self):
        changes = self.repo.git.log("origin/" + self.server.target_branch, pretty="oneline", max_count=1)
        return changes.split(" ")[0]

    def file_present(self, file_path):
        relative_path = os.path.relpath(file_path, str(self.root_directory))
        return relative_path in self.repo.git.ls_files(file_path)

    def text_in_file(self, text, file_path):
        relative_path = os.path.relpath(file_path, str(self.root_directory))
        return text in self.repo.git.show("HEAD:" + relative_path)

    def make_a_change(self):
        return self.server.make_a_change()


@pytest.fixture()
def git_client(git_server, tmpdir):
    yield GitClient(git_server, tmpdir)


class GitTestEnvironment(utils.BaseTestEnvironment):
    def __init__(self, client, directory, test_type):
        db_file = directory.join("gitpoll.json")
        super().__init__(client, directory, test_type, str(db_file))

        self.server = self.vcs_client.server
        self.vcs_client.repo.git.checkout(self.vcs_client.server.target_branch)

        self.settings.Vcs.type = "git"
        self.settings.GitVcs.repo = self.vcs_client.server.url
        self.settings.GitVcs.refspec = self.vcs_client.server.target_branch
        try:
            self.settings.GitSubmitVcs.user = "Testing User"
            self.settings.GitSubmitVcs.email = "some@email.com"
        except AttributeError:
            pass
