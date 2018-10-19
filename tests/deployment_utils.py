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
    def __init__(self, client, image, work_dir):
        self._image = image

        self._client = client
        self._work_dir = work_dir
        self._container = None

        self._volumes = {work_dir: {'bind': work_dir, 'mode': 'rw'}}
        self._environment = []

    def add_bind_dirs(self, directories):
        if self._container:
            raise Exception("Container is already running, no dirs can be bound!")
        for directory in directories:
            self._volumes[directory] = {'bind': directory, 'mode': 'rw'}

    def add_environment_variables(self, variables):
        if self._container:
            raise Exception("Container is already running, default environment cannot be changed!")
        self._environment.extend(variables)

    def start_container(self):
        if self._container:
            raise Exception("Docker container already running!")

        self._container = self._client.containers.run(self._image,
                                                      command="sleep infinity",
                                                      network_mode='host',
                                                      volumes=self._volumes,
                                                      environment=self._environment,
                                                      auto_remove=True,
                                                      detach=True)

    def get_working_directory(self):
        return self._work_dir

    def exit(self):
        try:
            user_id = getpwnam(getpass.getuser()).pw_uid
            for path in self._volumes:
                self._container.exec_run("chown -R {} {}".format(user_id, path))
            self._container.stop(timeout=0)
        except:
            if self._container:
                self._container.remove(force=True)
            raise

    def _run_and_check(self, cmd, result, environment=None):
        if not environment:
            environment = []
        process_id = self._client.api.exec_create(self._container.id, cmd, environment=environment)
        print "$ " + cmd
        log = self._client.api.exec_start(process_id)
        print log

        exit_code = self._client.api.exec_inspect(process_id)['ExitCode']
        if result:
            assert exit_code == 0
        else:
            assert exit_code != 0

        return log

    def assert_success(self, cmd, environment=None):
        return self._run_and_check(cmd, True, environment=environment)

    def assert_failure(self, cmd, environment=None):
        return self._run_and_check(cmd, False, environment=environment)


@pytest.fixture()
def command_runner(request, docker_registry_params):
    client = docker.from_env(timeout=1200)
    runner = None
    try:
        image = utils.get_image(request, client, docker_registry_params, "pythonp4")
        runner = CommandRunner(client, image, os.getcwd())
        yield runner
    finally:
        if runner:
            runner.exit()


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
        self.working_dir = self.command_runner.get_working_directory()
        self.project_root = os.path.join(self.working_dir, "temp")
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

        self.source_dir = os.path.join(self.working_dir, "examples")

        self.p4_path = "//depot/examples/..."
        self._init_p4()

        self.git_server = git_client.server.url
        self.git_branch = "examples"
        self._init_git()

        self.command_runner.add_environment_variables([
            "COVERAGE_FILE=" + self.command_runner.get_working_directory() + "/.coverage.docker"
        ])
        self.command_runner.add_bind_dirs([unicode(git_client.root_directory),
                                           git_client.server.get_location()])

        self.command_runner.start_container()
        log = self.command_runner.assert_success("pip install coverage")
        assert "Successfully installed" in log

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

    def run(self, config=None, force_installed=False, vcs_type="none",
            additional_parameters="", environment=None, expected_to_fail=False):

        if not config:
            config_file = "basic_config.py"
        else:
            config_file = os.path.join(self.working_dir, "temp_config.py")
            with open(config_file, 'wb+') as f:
                f.write(config)
                f.close()

        cmd = "coverage run --branch --append --source={} {}/universum.py" \
            .format(self.working_dir, self.working_dir)

        # We cannot collect coverage from installed module, so we run it only if specifically told so
        if force_installed:
            cmd = "universum"

        cmd += " -lcp {}".format(config_file) \
               + self._basic_args() + self._vcs_args(vcs_type) + additional_parameters

        if expected_to_fail:
            return self.command_runner.assert_failure(cmd, environment=environment)
        return self.command_runner.assert_success(cmd, environment=environment)

    def clean_artifacts(self):
        self.command_runner.assert_success("rm -rf {}".format(self.artifact_dir))


@pytest.fixture()
def universum_runner(command_runner, perforce_workspace, git_client):
    runner = UniversumRunner(command_runner, perforce_workspace, git_client)
    yield runner
    runner.clean_artifacts()
