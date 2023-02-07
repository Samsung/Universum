# pylint: disable = redefined-outer-name

import pathlib
import pytest
import P4

from . import utils
from .conftest import FuzzyCallChecker
from .deployment_utils import UniversumRunner
from .perforce_utils import P4TestEnvironment, PerforceWorkspace
from .utils import python, LocalTestEnvironment


def test_which_universum_is_tested(docker_main: UniversumRunner, pytestconfig):
    # THIS TEST PATCHES ACTUAL SOURCES! Discretion is advised
    init_file = pytestconfig.rootpath / "universum" / "__init__.py"
    backup = init_file.read_bytes()
    test_line = utils.randomize_name("THIS IS A TESTING VERSION")
    init_file.write_text(f"""__title__ = "Universum"
__version__ = "{test_line}"
""")
    output = docker_main.run(utils.simple_test_config, vcs_type="none")
    init_file.write_bytes(backup)
    assert test_line in output

    docker_main.environment.assert_successful_execution("pip uninstall -y universum")
    docker_main.run(utils.simple_test_config, vcs_type="none", force_installed=True, expected_to_fail=True)
    docker_main.clean_artifacts()
    docker_main.run(utils.simple_test_config, vcs_type="none")  # not expected to fail
    if utils.reuse_docker_containers():
        docker_main.environment.install_python_module(docker_main.working_dir)


@pytest.fixture(name='print_text_on_teardown')
def fixture_print_text_on_teardown():
    yield
    print("TearDown fixture output must be handled by 'detect_fails' fixture")


def test_teardown_fixture_output_verification(print_text_on_teardown: None):
    pass


@pytest.mark.parametrize("should_not_execute", [True, False], ids=['no-sources', 'deleted-sources'])
def test_clean_sources_exception(tmp_path: pathlib.Path, stdout_checker: FuzzyCallChecker, should_not_execute):
    env = LocalTestEnvironment(tmp_path, "main")
    env.settings.Vcs.type = "none"
    source_directory = tmp_path
    if should_not_execute:
        source_directory = source_directory / 'nonexisting_dir'
    env.settings.LocalMainVcs.source_dir = str(source_directory)
    env.configs_file.write_text(f"""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration",
                              command=["bash", "-c", "rm -rf {env.settings.ProjectDirectory.project_root}"])])
""")

    env.run(expect_failure=should_not_execute)
    error_message = f"[Errno 2] No such file or directory: '{env.settings.ProjectDirectory.project_root}'"
    stdout_checker.assert_has_calls_with_param(error_message)


def test_non_utf8_environment(docker_main: UniversumRunner):
    # POSIX has no 'UTF-8' in it's name, but supports Unicode
    output = docker_main.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="none", environment=['LANG=POSIX', 'LC_ALL=POSIX'])
    assert "\u2514" in output

    # 'en_US', unlike 'en_US.UTF-8', is latin-1
    docker_main.clean_artifacts()
    docker_main.environment.assert_successful_execution('apt install -y locales')
    docker_main.environment.assert_successful_execution('locale-gen --purge en_US')
    docker_main.environment.assert_successful_execution('update-locale LANG=en_US')
    output = docker_main.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="none", environment=['LANG=en_US', 'LC_ALL=en_US'])
    assert "\u2514" not in output


@pytest.fixture()
def perforce_environment(perforce_workspace: PerforceWorkspace, tmp_path: pathlib.Path):
    yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="main")


def test_p4_multiple_spaces_in_mappings(perforce_environment: P4TestEnvironment):
    perforce_environment.settings.PerforceWithMappings.project_depot_path = None
    perforce_environment.settings.PerforceWithMappings.mappings = [f"{perforce_environment.vcs_client.depot}   /..."]
    perforce_environment.run()


def test_p4_repository_difference_format(perforce_environment: P4TestEnvironment):
    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="This is a changed step name", command=["ls", "-la"])])
"""
    perforce_environment.shelve_config(config)
    perforce_environment.run()
    diff = (perforce_environment.artifact_dir / 'REPOSITORY_DIFFERENCE.txt').read_text()
    assert "This is a changed step name" in diff
    assert "b'" not in diff


@pytest.fixture()
def mock_opened(monkeypatch):
    def mocking_function(*args, **kwargs):
        raise P4.P4Exception("Client 'p4_disposable_workspace' unknown - use 'client' command to create it.")

    monkeypatch.setattr(P4.P4, 'run_opened', mocking_function, raising=False)


@utils.nox_only
def test_p4_failed_opened(perforce_environment: P4TestEnvironment, mock_opened: None):
    perforce_environment.run()


# TODO: move this test to 'test_api.py' after test refactoring and Docker use reduction
@utils.nox_only
def test_p4_api_failed_opened(perforce_environment: P4TestEnvironment, mock_opened: None):
    step_name = "API"
    config = f"""
from universum.configuration_support import Step, Configuration

configs = Configuration([Step(name="{step_name}", artifacts="output.json",
                              command=["bash", "-c", "{python()} -m universum api file-diff > output.json"])])
    """
    perforce_environment.shelve_config(config)
    perforce_environment.settings.Launcher.output = "file"

    perforce_environment.run()
    log = (perforce_environment.artifact_dir / f'{step_name}_log.txt').read_text()
    assert "Module sh got exit code 1" in log
    assert "Getting file diff failed due to Perforce server internal error" in log


def test_p4_clean_empty_cl(perforce_environment: P4TestEnvironment, stdout_checker: FuzzyCallChecker):
    # This test creates an empty CL, triggering "file(s) not opened on this client" exception on cleanup
    # Wrong exception handling prevented further client cleanup on force clean, making final client deleting impossible

    config = f"""
from universum.configuration_support import Step, Configuration

configs = Configuration([Step(name="Create empty CL",
                              command=["bash", "-c",
                              "p4 --field 'Description=My pending change' --field 'Files=' change -o | p4 change -i"],
                              environment = {{"P4CLIENT": "{perforce_environment.client_name}",
                                              "P4PORT": "{perforce_environment.vcs_client.p4.port}",
                                              "P4USER": "{perforce_environment.vcs_client.p4.user}",
                                              "P4PASSWD": "{perforce_environment.vcs_client.p4.password}"}})])
"""
    perforce_environment.shelve_config(config)
    perforce_environment.run()
    error_message = f"""[Error]: "Client '{perforce_environment.client_name}' has pending changes."""
    stdout_checker.assert_absent_calls_with_param(error_message)


@pytest.fixture()
def perforce_environment_with_files(perforce_environment: P4TestEnvironment):
    files = [perforce_environment.vcs_client.create_file(utils.randomize_name("new_file") + ".txt")
             for _ in range(2)]

    yield {"env": perforce_environment, "files": files}

    for entry in files:
        perforce_environment.vcs_client.delete_file(entry.name)


def test_success_p4_resolve_unshelved(perforce_environment_with_files: dict, stdout_checker: FuzzyCallChecker):
    p4_file = perforce_environment_with_files["files"][0]
    env = perforce_environment_with_files["env"]
    config = f"""
from universum.configuration_support import Step, Configuration

configs = Configuration([Step(name="Print file", command=["bash", "-c", "cat '{p4_file.name}'"])])
"""
    env.shelve_config(config)
    cls = [env.vcs_client.shelve_file(p4_file, "This is changed line 1\nThis is unchanged line 2"),
           env.vcs_client.shelve_file(p4_file, "This is unchanged line 1\nThis is changed line 2")]
    env.settings.PerforceMainVcs.shelve_cls.extend(cls)

    env.run()
    stdout_checker.assert_has_calls_with_param("This is changed line 1")
    stdout_checker.assert_has_calls_with_param("This is changed line 2")


def test_fail_p4_resolve_unshelved(perforce_environment_with_files: dict, stdout_checker: FuzzyCallChecker):
    p4_file = perforce_environment_with_files["files"][0]
    env = perforce_environment_with_files["env"]
    config = f"""
from universum.configuration_support import Step, Configuration

configs = Configuration([Step(name="Print file", command=["bash", "-c", "cat '{p4_file.name}'"])])
"""
    env.shelve_config(config)
    cls = [env.vcs_client.shelve_file(p4_file, "This is changed line 1\nThis is unchanged line 2"),
           env.vcs_client.shelve_file(p4_file, "This is a different line 1\nThis is changed line 2")]
    env.settings.PerforceMainVcs.shelve_cls.extend(cls)

    env.run(expect_failure=True)
    stdout_checker.assert_has_calls_with_param("Problems during merge while resolving shelved CLs")
    stdout_checker.assert_has_calls_with_param(str(p4_file.name))


def test_success_p4_resolve_unshelved_multiple(perforce_environment_with_files: dict):
    p4_files = perforce_environment_with_files["files"]
    env = perforce_environment_with_files["env"]
    config = """
from universum.configuration_support import Step, Configuration

configs = Configuration([Step(name="Step one", command=["ls", "-l"])])
"""
    env.shelve_config(config)
    cl_1 = env.vcs_client.shelve_file(p4_files[0], "This is changed line 1\nThis is unchanged line 2")
    env.vcs_client.shelve_file(p4_files[1], "This is changed line 1\nThis is unchanged line 2", shelve_cl=cl_1)
    cl_2 = env.vcs_client.shelve_file(p4_files[0], "This is unchanged line 1\nThis is changed line 2")
    env.vcs_client.shelve_file(p4_files[1], "This is unchanged line 1\nThis is changed line 2", shelve_cl=cl_2)
    env.settings.PerforceMainVcs.shelve_cls.extend([cl_1, cl_2])

    env.run()
    repo_state = (env.artifact_dir / 'REPOSITORY_STATE.txt').read_text()
    assert p4_files[0].name in repo_state
    assert p4_files[1].name in repo_state


def test_exit_code_failed_report(perforce_environment: P4TestEnvironment):
    """
    This test checks for previous bug where exceptions during result reporting led to exit code 0
    even when '--fail-unsuccessful' option was enabled (and some steps failed)
    """
    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Unsuccessful step", command=["exit", "1"])])
"""
    perforce_environment.shelve_config(config)
    perforce_environment.settings.MainVcs.report_to_review = True
    perforce_environment.settings.Swarm.server_url = "some_server"
    perforce_environment.settings.Swarm.review_id = "some_id"
    perforce_environment.settings.Swarm.change = perforce_environment.settings.PerforceMainVcs.shelve_cls[0]
    perforce_environment.settings.Main.fail_unsuccessful = True

    perforce_environment.run(expect_failure=True)
