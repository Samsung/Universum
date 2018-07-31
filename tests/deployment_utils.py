# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import getpass
from pwd import getpwnam
import os

import docker

import pytest
from . import utils


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
    client = docker.from_env(timeout=600)
    container = None
    runner = None
    bind_dir = "/host"
    try:
        try:
            image = utils.get_image(request, client, docker_registry_params, "pythonp4")
            container = client.containers.run(image,
                                              command="sleep infinity",
                                              volumes={os.getcwd(): {'bind': bind_dir, 'mode': 'rw'}},
                                              network_mode='host',
                                              auto_remove=True,
                                              detach=True)
            runner = CommandRunner(client, container, bind_dir)
            yield runner
        finally:
            if runner is not None:
                runner.exit()
    except:
        if container is not None:
            container.remove(force=True)
        raise


class RunBaseConfig(object):
    def __init__(self, command_runner):
        self.command_runner = command_runner
        self.working_dir = command_runner.get_working_directory()
        self.source_dir = os.path.join(self.working_dir, "examples")
        self.project_root = os.path.join(self.working_dir, "temp")
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

    def install_env(self):
        log = self.command_runner.assert_success("pip install " + self.working_dir)
        assert "Successfully installed" in log

    def run_from_source(self, config_file):
        cmd = "universum -vt none -lo console -fsd {0} -lcp {1} -pr {2} -ad {3}". \
            format(self.source_dir, config_file, self.project_root, self.artifact_dir)
        log = self.command_runner.assert_success(cmd)
        return log


@pytest.fixture()
def universum_runner(command_runner):
    setup = RunBaseConfig(command_runner)
    setup.install_env()
    yield setup
