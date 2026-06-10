# pylint: disable = redefined-outer-name

import pathlib
import pytest

from . import utils
from .conftest import FuzzyCallChecker
from .deployment_utils import UniversumRunner
from .utils import LocalTestEnvironment


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

    docker_main.environment.assert_successful_execution("pip uninstall --break-system-packages -y universum")
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


@pytest.mark.xfail
def test_non_utf8_environment(docker_main: UniversumRunner):
    # POSIX has no 'UTF-8' in its name, but supports Unicode
    output = docker_main.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="none", environment=['LANG=POSIX', 'LC_ALL=POSIX'])
    assert "\u2514" in output  # I guess this problem doesn't reproduce on newer systems

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
