# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import getpass
from pwd import getpwnam
import os

import docker

import pytest
from . import utils


class ExecutionEnvironment(object):
    def __init__(self, request, work_dir):
        self.request = request
        self._image = None
        self._container = None
        self._work_dir = work_dir

        self._client = docker.from_env(timeout=1200)

        self._volumes = {work_dir: {'bind': work_dir, 'mode': 'rw'}}
        self._environment = []

    def set_image(self, image_name, params):
        self._image = utils.get_image(self.request, self._client, params, image_name)

    def add_bind_dirs(self, directories):
        if self._container:
            self.request.raiseerror("Container is already running, no dirs can be bound!")
        for directory in directories:
            self._volumes[directory] = {'bind': directory, 'mode': 'rw'}

    def add_environment_variables(self, variables):
        if self._container:
            self.request.raiseerror("Container is already running, default environment cannot be changed!")
        self._environment.extend(variables)

    def start_container(self):
        if self._container:
            self.request.raiseerror("Docker container already running!")
        if not self._image:
            self.request.raiseerror("Please get a docker image for this container!")

        self._container = self._client.containers.run(self._image,
                                                      command="sleep infinity",
                                                      network_mode='host',
                                                      volumes=self._volumes,
                                                      environment=self._environment,
                                                      auto_remove=True,
                                                      detach=True)

    def get_working_directory(self):
        return self._work_dir

    def _run_and_check(self, cmd, result, environment):
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

    def assert_successful_execution(self, cmd, environment=None):
        return self._run_and_check(cmd, True, environment=environment)

    def assert_unsuccessful_execution(self, cmd, environment=None):
        return self._run_and_check(cmd, False, environment=environment)

    def install_pip(self):
        self.assert_successful_execution("apt-get update")
        self.assert_successful_execution("apt-get install -y wget")
        self.assert_successful_execution(
            "wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'"
        )
        self.assert_successful_execution("apt-get install -y python")
        log = self.assert_successful_execution("python get-pip.py")
        assert "Successfully installed" in log

    def install_python_module(self, name):
        cmd = "pip --default-timeout=1200 install " + name
        log = self.assert_successful_execution(cmd)
        assert "Successfully installed" in log

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


@pytest.fixture()
def execution_environment(request):
    runner = None
    try:
        runner = ExecutionEnvironment(request, os.getcwd())
        yield runner
    finally:
        if runner:
            runner.exit()


@pytest.fixture()
def pythonp4_environment(execution_environment, docker_registry_params):
    execution_environment.set_image("pythonp4", docker_registry_params)
    yield execution_environment


@pytest.fixture()
def plain_ubuntu_environment(execution_environment, docker_registry_params):
    execution_environment.set_image("ubuntu:trusty", docker_registry_params)
    yield execution_environment


@pytest.fixture()
def local_sources(tmpdir):
    source_dir = tmpdir.mkdir("project_sources")
    local_file = source_dir.join("readme.txt")
    local_file.write("This is a an empty file")

    yield utils.Params(root_directory=source_dir, repo_file=local_file)


class UniversumRunner(object):
    def __init__(self, execution_environment, perforce_workspace, git_client, local_sources):
        self.perforce = perforce_workspace
        self.git = git_client
        self.local = local_sources

        self.environment = execution_environment
        self.working_dir = self.environment.get_working_directory()
        self.project_root = os.path.join(self.working_dir, "temp")
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

        self.environment.add_environment_variables([
            "COVERAGE_FILE=" + self.environment.get_working_directory() + "/.coverage.docker"
        ])
        self.environment.add_bind_dirs([unicode(local_sources.root_directory),
                                        git_client.server.get_location()])

        self.environment.start_container()

    def _basic_args(self):
        return " -lo console -pr {} -ad {}".format(self.project_root, self.artifact_dir)

    def _vcs_args(self, vcs_type):
        if vcs_type == "none":
            return " -vt none -fsd {}".format(unicode(self.local.root_directory))

        if vcs_type == "git":
            return " -vt git -gr {} -grs {}".format(self.git.server.url, self.git.server.target_branch)

        return " -vt p4 --p4-force-clean -p4p {} -p4u {} -p4P {} -p4d {} -p4c {}" \
            .format(self.perforce.p4.port,
                    self.perforce.p4.user,
                    self.perforce.p4.password,
                    self.perforce.depot,
                    "my_disposable_p4_client")

    def run(self, config, force_installed=False, vcs_type="none",
            additional_parameters="", environment=None, expected_to_fail=False):

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
            return self.environment.assert_unsuccessful_execution(cmd, environment=environment)
        return self.environment.assert_successful_execution(cmd, environment=environment)

    def clean_artifacts(self):
        self.environment.assert_successful_execution("rm -rf {}".format(self.artifact_dir))


@pytest.fixture()
def universum_runner_no_gitpython(pythonp4_environment, perforce_workspace, git_client, local_sources):
    runner = UniversumRunner(pythonp4_environment, perforce_workspace, git_client, local_sources)
    runner.environment.install_python_module(runner.working_dir)
    runner.environment.install_python_module("coverage")
    yield runner
    runner.clean_artifacts()


@pytest.fixture()
def universum_runner(universum_runner_no_gitpython):
    universum_runner_no_gitpython.environment.install_python_module("gitpython")
    yield universum_runner_no_gitpython


@pytest.fixture()
def universum_runner_plain_ubuntu(plain_ubuntu_environment, perforce_workspace, git_client, local_sources):
    runner = UniversumRunner(plain_ubuntu_environment, perforce_workspace, git_client, local_sources)
    runner.environment.install_pip()
    runner.environment.install_python_module(runner.working_dir)
    runner.environment.install_python_module("coverage")
    yield runner
    runner.clean_artifacts()
