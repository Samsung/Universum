# pylint: disable = redefined-outer-name

import getpass
import os
from pwd import getpwnam

import docker
import py
import pytest
from requests.exceptions import ReadTimeout

from . import utils


class ExecutionEnvironment:
    def __init__(self, request, work_dir, force_clean=False):
        self.request = request
        self._force_clean = force_clean
        self._image = None
        self._image_name = None
        self._container = None
        self._container_id = None
        self._work_dir = work_dir

        self._client = docker.from_env(timeout=1200)

        self._volumes = {work_dir: {'bind': work_dir, 'mode': 'rw'}}
        self._environment = []

    def set_image(self, image_name):
        self._image_name = image_name
        self._image = self._client.images.get(image_name)
        self._container_id = utils.randomize_name("ci_test_" + image_name + "-")
        if utils.is_pycharm() and not self._force_clean:
            self._container_id = self.request.config.cache.get("ci_test/" + self._image_name, self._container_id)

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

        try:
            self._container = self._client.containers.get(self._container_id)
            if not utils.is_container_outdated(self._container):
                return False
        except docker.errors.NotFound:
            pass

        self._container = self._client.containers.run(self._image,
                                                      name=self._container_id,
                                                      command="sleep infinity",
                                                      network_mode='host',
                                                      volumes=self._volumes,
                                                      environment=self._environment,
                                                      auto_remove=True,
                                                      detach=True,
                                                      security_opt=['seccomp=unconfined'])
        return True

    def get_working_directory(self):
        return self._work_dir

    def _run_and_check(self, cmd, result, environment, workdir):
        if not environment:
            environment = []
        process_id = self._client.api.exec_create(self._container.id, cmd, environment=environment, workdir=workdir)
        print("$ " + cmd)
        log = self._client.api.exec_start(process_id)
        assert not isinstance(str, type(log)), "Looks like it's a bug in a docker 4.1.0. According to documentation " \
                                               "this function must return 'str'. However it returns 'bytes'"
        log = log.decode("utf-8")
        print(log)

        exit_code = self._client.api.exec_inspect(process_id)['ExitCode']
        if result:
            assert exit_code == 0
        else:
            assert exit_code != 0

        return log

    def assert_successful_execution(self, cmd, environment=None, workdir=None):
        return self._run_and_check(cmd, True, environment=environment, workdir=workdir)

    def assert_unsuccessful_execution(self, cmd, environment=None, workdir=None):
        return self._run_and_check(cmd, False, environment=environment, workdir=workdir)

    def install_python_module(self, name):
        if os.path.exists(name):
            module_name = 'universum'
            name = f"'{name}'"
        else:
            module_name = name
        if not utils.is_pycharm() or self._force_clean:
            self.assert_unsuccessful_execution("pip show " + module_name)
        cmd = "pip --default-timeout=1200 install " + name
        self.assert_successful_execution(cmd)
        self.assert_successful_execution("pip show " + module_name)

    def exit(self):
        try:
            user_id = getpwnam(getpass.getuser()).pw_uid
            for path in self._volumes:
                self._container.exec_run("chown -R {} {}".format(user_id, path))
            if utils.is_pycharm() and not self._force_clean:
                self.request.config.cache.set("ci_test/" + self._image_name, self._container_id)
            else:
                try:
                    self._container.stop(timeout=0)
                except ReadTimeout:
                    pass
        except:
            if self._container:
                self._container.remove(force=True)
            raise


@pytest.fixture()
def execution_environment(request) -> ExecutionEnvironment:
    runner = None
    try:
        runner = ExecutionEnvironment(request, os.getcwd())
        yield runner
    finally:
        if runner:
            runner.exit()


@pytest.fixture()
def clean_execution_environment(request):
    runner = None
    try:
        runner = ExecutionEnvironment(request, os.getcwd(), force_clean=True)
        yield runner
    finally:
        if runner:
            runner.exit()


@pytest.fixture()
def local_sources(tmpdir):
    if utils.is_pycharm():
        source_dir = py.path.local(".work").ensure(dir=True)
    else:
        source_dir = tmpdir.mkdir("project_sources")
    local_file = source_dir.join("readme.txt")
    local_file.write("This is a an empty file")

    yield utils.Params(root_directory=source_dir, repo_file=local_file)


class UniversumRunner:
    def __init__(self, perforce_workspace, git_client, local_sources, nonci):
        self.perforce = perforce_workspace
        self.git = git_client
        self.local = local_sources
        self.nonci = nonci

        # Need to be initialized in 'set_environment'
        self.environment = None
        self.working_dir: str = None
        self.project_root = None
        self.artifact_dir = None

    def set_environment(self, execution_environment):
        self.environment = execution_environment
        self.working_dir = self.environment.get_working_directory()
        self.project_root = os.path.join(self.working_dir, "temp")
        if self.nonci:
            self.project_root = self.local.root_directory
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

        self.environment.add_environment_variables([
            "COVERAGE_FILE=" + self.environment.get_working_directory() + "/.coverage.docker"
        ])
        self.environment.add_bind_dirs([str(self.local.root_directory)])

        if self.environment.start_container():
            self.environment.install_python_module(self.working_dir)
            self.environment.install_python_module("coverage")

    def _basic_args(self):
        return " -lo console -ad '{}'".format(self.artifact_dir)

    def _mandatory_args(self, config_file):
        result = f" -lcp '{config_file}'"
        if self.project_root:
            result += f" -pr '{self.project_root}'"
        return result

    def _vcs_args(self, vcs_type):
        if vcs_type == "none":
            return " -vt none -fsd '{}'".format(str(self.local.root_directory))

        if vcs_type == "git":
            return " -vt git -gr '{}' -grs '{}'".format(self.git.server.url, self.git.server.target_branch)

        return " -vt p4 --p4-force-clean -p4p '{}' -p4u '{}' -p4P '{}' -p4d '{}' -p4c {}" \
            .format(self.perforce.p4.port,
                    self.perforce.p4.user,
                    self.perforce.p4.password,
                    self.perforce.depot,
                    "my_disposable_p4_client")

    def _create_temp_config(self, config: str):
        file_path = os.path.join(self.working_dir, "temp_config.py")
        with open(file_path, 'w+') as f:
            f.write(config)
        return file_path

    def run(self, config: str, force_installed: bool = False, vcs_type: str = "none",
            additional_parameters="", environment=None, expected_to_fail=False, workdir=None):

        if utils.is_pycharm():
            cmd = "{0}/universum/__main__.py".format(self.working_dir)
        else:
            cmd = "coverage run --branch --append --source='{0}' '{0}/universum/__main__.py'" \
                .format(self.working_dir)

        # We cannot collect coverage from installed module, so we run it only if specifically told so
        if force_installed:
            cmd = "python3.7 -m universum"

        if self.nonci:
            cmd += ' nonci'
        else:
            cmd += self._basic_args() + self._vcs_args(vcs_type)

        config_file = self._create_temp_config(config)
        cmd += self._mandatory_args(config_file) + ' ' + additional_parameters

        if expected_to_fail:
            result = self.environment.assert_unsuccessful_execution(cmd, environment=environment, workdir=workdir)
        else:
            result = self.environment.assert_successful_execution(cmd, environment=environment, workdir=workdir)

        os.remove(config_file)
        return result

    def clean_artifacts(self):
        self.environment.assert_successful_execution("rm -rf '{}'".format(self.artifact_dir))


@pytest.fixture()
def runner_without_environment(perforce_workspace, git_client, local_sources) -> UniversumRunner:
    runner = UniversumRunner(perforce_workspace, git_client, local_sources, nonci=False)
    yield runner
    runner.clean_artifacts()


@pytest.fixture()
def docker_main_with_vcs(execution_environment, runner_without_environment):
    execution_environment.set_image("universum_test_env")
    runner_without_environment.set_environment(execution_environment)
    yield runner_without_environment


def docker_fixture_template(request, execution_environment, local_sources):
    runner = UniversumRunner(None, None, local_sources, nonci=request.param)
    execution_environment.set_image("universum_test_env")
    runner.set_environment(execution_environment)
    yield runner
    runner.clean_artifacts()


docker_main = pytest.fixture(params=[False])(docker_fixture_template)
docker_nonci = pytest.fixture(params=[True])(docker_fixture_template)
docker_main_and_nonci = pytest.fixture(params=[False, True], ids=["main", "nonci"])(docker_fixture_template)


@pytest.fixture()
def clean_docker_main(clean_execution_environment, runner_without_environment):
    clean_execution_environment.set_image("universum_test_env")
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment


@pytest.fixture()
def clean_docker_main_no_p4(clean_execution_environment, runner_without_environment):
    clean_execution_environment.set_image("universum_test_env_no_p4")
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment


@pytest.fixture()
def clean_docker_main_no_vcs(clean_execution_environment, runner_without_environment):
    clean_execution_environment.set_image("universum_test_env_no_vcs")
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment
