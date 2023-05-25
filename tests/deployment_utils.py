# pylint: disable = redefined-outer-name

import getpass
import os
import shutil
import pathlib
from pwd import getpwnam

import docker
import pytest
from requests.exceptions import ReadTimeout

from . import utils
from .git_utils import GitClient
from .perforce_utils import PerforceWorkspace
from .utils import python


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
        self._container_id = utils.randomize_name("ci_test_" + image_name)
        if utils.reuse_docker_containers() and not self._force_clean:
            self._container_id = self.request.config.cache.get("ci_test/" + self._image_name, self._container_id)

    def add_bind_dirs(self, directories):
        if self._container:
            self.request.raiseerror("Container is already running, no dirs can be bound!")
        for directory in directories:
            absolute_dir = str(pathlib.Path(directory).absolute())
            self._volumes[absolute_dir] = {'bind': absolute_dir, 'mode': 'rw'}

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
        if not utils.reuse_docker_containers() or self._force_clean:
            self.assert_unsuccessful_execution("pip show " + module_name)
        # in PyCharm modules are already installed and therefore should be updated
        cmd = "pip --default-timeout=1200 install -U " + name
        self.assert_successful_execution(cmd)
        self.assert_successful_execution("pip show " + module_name)

    def exit(self):
        try:
            user_id = getpwnam(getpass.getuser()).pw_uid
            for path in self._volumes:
                self._container.exec_run(f"chown -R {user_id} {path}")
            if utils.reuse_docker_containers() and not self._force_clean:
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
def execution_environment(request):
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


class LocalSources(utils.BaseVcsClient):
    def __init__(self, root_directory: pathlib.Path, repo_file: pathlib.Path):
        super().__init__()
        self.root_directory = root_directory
        self.repo_file = repo_file


@pytest.fixture()
def local_sources(tmp_path: pathlib.Path):
    if utils.reuse_docker_containers():
        source_dir = pathlib.Path(".work")
        try:
            shutil.rmtree(source_dir, ignore_errors=True)
        except OSError:
            pass
        source_dir.mkdir()

    else:
        source_dir = tmp_path / "project_sources"
        source_dir.mkdir()
    local_file = source_dir / "readme.txt"
    local_file.write_text("This is a an empty file", encoding="utf-8")

    yield LocalSources(root_directory=source_dir, repo_file=local_file)


class UniversumRunner:
    def __init__(self, perforce_workspace: PerforceWorkspace,
                 git_client: GitClient,
                 local_sources: LocalSources,
                 nonci: bool):
        self.perforce: PerforceWorkspace = perforce_workspace
        self.git: GitClient = git_client
        self.local: LocalSources = local_sources
        self.nonci: bool = nonci

        # Need to be initialized in 'set_environment'
        self.environment: ExecutionEnvironment = None  # type: ignore
        self.working_dir: str = None  # type: ignore
        self.project_root: str = None  # type: ignore
        self.artifact_dir: str = None  # type: ignore

    def set_environment(self, execution_environment: ExecutionEnvironment) -> None:
        self.environment = execution_environment
        self.working_dir = self.environment.get_working_directory()
        self.project_root = os.path.join(self.working_dir, "temp")
        if self.nonci:
            self.project_root = str(self.local.root_directory)
        self.artifact_dir = os.path.join(self.working_dir, "artifacts")

        self.environment.add_environment_variables([
            "COVERAGE_FILE=" + self.environment.get_working_directory() + "/.coverage.docker"
        ])
        self.environment.add_bind_dirs([str(self.local.root_directory)])

        if self.environment.start_container():
            self.environment.install_python_module(self.working_dir)
            self.environment.install_python_module("coverage")

    def _mandatory_args(self, config_file: str) -> str:
        result = f" -lcp '{config_file}' -ad '{self.artifact_dir}'"
        if self.project_root:
            result += f" -pr '{self.project_root}'"
        return result

    def _vcs_args(self, vcs_type: str) -> str:
        if vcs_type == "none":
            return f" -vt none -fsd '{self.local.root_directory}'"

        if vcs_type == "git":
            return f" -vt git -gr '{self.git.server.url}' -grs '{self.git.server.target_branch}'"

        return f" -vt p4 --p4-force-clean" \
               f" -p4p '{self.perforce.server.port}'" \
               f" -p4u '{self.perforce.server.user}'" \
               f" -p4P '{self.perforce.server.password}'" \
               f" -p4d '{self.perforce.depot}'" \
               f" -p4c 'my_disposable_p4_client'"

    def _create_temp_config(self, config: str) -> str:
        file_path = os.path.join(self.working_dir, "temp_config.py")
        with open(file_path, 'w+', encoding="utf-8") as f:
            f.write(config)
        return file_path

    def run(self, config: str, force_installed: bool = False, vcs_type: str = "none",
            additional_parameters="", environment=None, expected_to_fail=False, workdir=None) -> str:
        """
        `force_installed` launches python with '-I' option, that ensures the non-installed universum sources
        will not be used instead of those installed into system. Without '-I' option `python -m` will first
        try to launch universum from sources in `workdir` if there are any. That is why, if `workdir` is not
        default and there are no universum sources in specified `workdir`, the preinstalled universum will
        be ran as in case of `force_installed`.
        """

        if force_installed:
            cmd = f"{python()} -I -m universum"
        elif utils.reuse_docker_containers() or workdir:
            cmd = f"{python()} -m universum"
        else:
            cmd = f"coverage run --branch --append --source='{self.working_dir}' -m universum"

        if self.nonci:
            cmd += ' nonci'
        else:
            cmd += " -lo console" + self._vcs_args(vcs_type)

        config_file = self._create_temp_config(config)
        cmd += self._mandatory_args(config_file) + ' ' + additional_parameters

        # if workdir is None, cmd will be launched from '/', which is clearly not a directory with universum sources
        if not workdir:
            workdir = self.working_dir

        if expected_to_fail:
            result = self.environment.assert_unsuccessful_execution(cmd, environment=environment, workdir=workdir)
        else:
            result = self.environment.assert_successful_execution(cmd, environment=environment, workdir=workdir)

        os.remove(config_file)
        return result

    def clean_artifacts(self) -> None:
        self.environment.assert_successful_execution(f"rm -rf '{self.artifact_dir}'")


@pytest.fixture()
def runner_without_environment(perforce_workspace: PerforceWorkspace, git_client: GitClient, local_sources: LocalSources):
    runner = UniversumRunner(perforce_workspace, git_client, local_sources, nonci=False)
    yield runner
    runner.clean_artifacts()


@pytest.fixture()
def docker_main_with_vcs(execution_environment: ExecutionEnvironment, runner_without_environment: UniversumRunner):
    execution_environment.set_image("universum_test_env_" + python())
    runner_without_environment.set_environment(execution_environment)
    yield runner_without_environment


def docker_fixture_template(request, execution_environment: ExecutionEnvironment, local_sources: LocalSources):
    runner = UniversumRunner(None, None, local_sources, nonci=request.param)  # type: ignore
    execution_environment.set_image("universum_test_env_" + python())
    runner.set_environment(execution_environment)
    yield runner
    runner.clean_artifacts()


docker_main = pytest.fixture(params=[False], ids=["main"])(docker_fixture_template)
docker_nonci = pytest.fixture(params=[True], ids=["nonci"])(docker_fixture_template)
docker_main_and_nonci = pytest.fixture(params=[False, True], ids=["main", "nonci"])(docker_fixture_template)


@pytest.fixture()
def clean_docker_main(clean_execution_environment: ExecutionEnvironment, runner_without_environment: UniversumRunner):
    clean_execution_environment.set_image("universum_test_env_" + python())
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment


@pytest.fixture()
def clean_docker_main_no_p4(clean_execution_environment: ExecutionEnvironment, runner_without_environment: UniversumRunner):
    clean_execution_environment.set_image("universum_test_env_no_p4_" + python())
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment


@pytest.fixture()
def clean_docker_main_no_vcs(clean_execution_environment: ExecutionEnvironment, runner_without_environment: UniversumRunner):
    clean_execution_environment.set_image("universum_test_env_no_vcs_" + python())
    runner_without_environment.set_environment(clean_execution_environment)
    yield runner_without_environment
