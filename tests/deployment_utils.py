# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

from distutils import dir_util
import getpass
from pwd import getpwnam
import os
import shutil

import docker

import pytest
from . import utils
from .perforce_utils import ignore_p4_exception


class CommandRunner(object):
    def __init__(self, client, container, bound_dir):
        self._client = client
        self._container = container
        self._bound_dir = bound_dir

    def get_working_directory(self):
        return self._bound_dir

    def exit(self):
        user_id = getpwnam(getpass.getuser()).pw_uid
        self._container.exec_run("chown -R {} {}".format(user_id, self._bound_dir))
        self._container.stop(timeout=0)

    def _run_and_check(self, cmd, result):
        process_id = self._client.api.exec_create(self._container.id, cmd)
        print "$ " + cmd
        log = self._client.api.exec_start(process_id)
        print log

        exit_code = self._client.api.exec_inspect(process_id)['ExitCode']
        if result:
            assert exit_code == 0
        else:
            assert exit_code != 0

        return log

    def assert_success(self, cmd):
        return self._run_and_check(cmd, True)

    def assert_failure(self, cmd):
        return self._run_and_check(cmd, False)


@pytest.fixture()
def command_runner(request, docker_registry_params):
    client = docker.from_env(timeout=1200)
    container = None
    runner = None
    bind_dir = os.getcwd()
    try:
        try:
            image = utils.get_image(request, client, docker_registry_params, "pythonp4")
            container = client.containers.run(image,
                                              command="sleep infinity",
                                              volumes={os.getcwd(): {'bind': bind_dir, 'mode': 'rw'}},
                                              network_mode='host',
                                              environment=["COVERAGE_FILE=" + bind_dir + "/.coverage.docker"],
                                              auto_remove=True,
                                              detach=True)
            runner = CommandRunner(client, container, bind_dir)
            runner.assert_success("pip install coverage")
            yield runner
        finally:
            if runner is not None:
                runner.exit()
    except:
        if container is not None:
            container.remove(force=True)
        raise


class UniversumRunner(object):

    def _init_p4(self):
        p4_dir = unicode(self.perforce_workspace.root_directory.join("examples"))
        try:
            shutil.copytree(self.source_dir, p4_dir)
        except OSError:
            shutil.rmtree(p4_dir)
            shutil.copytree(self.source_dir, p4_dir)

        def update_directory(workspace, directory):
            workspace.p4.run_reconcile("-a", "-e", "-d", directory)
            change = workspace.p4.run_change("-o")[0]
            change["Description"] = "Update directory " + str(os.path.basename(directory))
            workspace.p4.run_submit(change)

        ignore_p4_exception("no file(s) to reconcile", update_directory,
                            self.perforce_workspace, p4_dir + "/...")

    def _init_git(self):
        configurator = self.git_client.repo.config_writer()
        configurator.set_value("user", "name", "Testing user")
        configurator.set_value("user", "email", "some@email.com")
        configurator.set_value("push", "default", "matching")

        self.git_client.repo.git.checkout(b=self.git_branch)
        git_dir = unicode(self.git_client.root_directory)
        dir_util.copy_tree(self.source_dir, git_dir)

        self.git_client.repo.git.add(all=True)
        description = "Update 'examples'"
        self.git_client.repo.git.commit(m=description)
        self.git_client.repo.remotes.origin.push(self.git_branch, progress=self.git_client.logger)

    def __init__(self, command_runner, perforce_workspace, git_client):
        self.command_runner = command_runner
        self.perforce_workspace = perforce_workspace
        self.git_client = git_client
        self.working_dir = command_runner.get_working_directory()
        self.project_root = os.path.join(self.working_dir, "temp")
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

        self.source_dir = os.path.join(self.working_dir, "examples")

        self.p4_path = "//depot/examples/..."
        self._init_p4()

        # TODO: remove copying the server to workdir
        self._local_git_server = os.path.join(os.getcwd(), "local_git_server")
        self.git_server = "file://" + unicode(self._local_git_server)
        self.git_branch = "examples"
        self._init_git()
        shutil.copytree(unicode(self.git_client.server._working_directory),  # pylint: disable=protected-access
                        self._local_git_server)

    def install_env(self):
        log = self.command_runner.assert_success("pip --default-timeout=1200 install " + self.working_dir)
        assert "Successfully installed" in log

    def _basic_args(self):
        return " -lo console -pr {} -ad {}".format(self.project_root, self.artifact_dir)

    def _vcs_args(self, vcs_type):
        if vcs_type == "none":
            return " -vt none -fsd {}".format(self.source_dir)

        if vcs_type == "git":
            return " -vt git -gr {} -grs {}".format(self.git_server, self.git_branch)

        return " -vt p4 --p4-force-clean -p4p {} -p4u {} -p4P {} -p4d {} -p4c {}" \
            .format(self.perforce_workspace.p4.port,
                    self.perforce_workspace.p4.user,
                    self.perforce_workspace.p4.password,
                    self.p4_path,
                    "my_disposable_p4_client")

    def run_installed(self, config_file, vcs_type="none"):
        cmd = "universum -lcp {}".format(config_file) + self._basic_args() + self._vcs_args(vcs_type)
        return self.command_runner.assert_success(cmd)

    def run_with_coverage(self, config_file, vcs_type="none"):
        cmd = "coverage run --branch --append --source={} {}/universum.py -lcp {}"\
            .format(self.working_dir, self.working_dir, config_file)
        cmd += self._basic_args() + self._vcs_args(vcs_type)
        return self.command_runner.assert_success(cmd)

    def clean_artifacts(self):
        self.command_runner.assert_success("rm -rf {}".format(self.artifact_dir))

    def clean_git_server(self):
        shutil.rmtree(self._local_git_server)


@pytest.fixture()
def universum_runner(command_runner, perforce_workspace, git_client):
    runner = UniversumRunner(command_runner, perforce_workspace, git_client)
    runner.install_env()
    yield runner
    runner.clean_artifacts()
    runner.clean_git_server()
