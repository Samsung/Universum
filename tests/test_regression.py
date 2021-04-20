# pylint: disable = redefined-outer-name

import pytest
import P4

from universum import __main__
from . import utils
from .perforce_utils import P4Environment


@pytest.fixture(name='print_text_on_teardown')
def fixture_print_text_on_teardown():
    yield
    print("TearDown fixture output must be handled by 'detect_fails' fixture")


def test_teardown_fixture_output_verification(print_text_on_teardown):
    pass


def test_clean_sources_exceptions(tmpdir):
    env = utils.TestEnvironment(tmpdir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmpdir / 'nonexisting_dir')

    # Check failure with non-existing temp dir
    __main__.run(env.settings)
    # the log output is automatically checked by the 'detect_fails' fixture

    # Check failure with temp dir deleted by the launched project
    env.settings.LocalMainVcs.source_dir = str(tmpdir)
    env.configs_file.write("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["bash", "-c", "rm -rf {}"])])
""".format(env.settings.ProjectDirectory.project_root))

    __main__.run(env.settings)
    # the log output is automatically checked by the 'detect_fails' fixture


def test_non_utf8_environment(docker_main):
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
def perforce_environment(perforce_workspace, tmpdir):
    yield P4Environment(perforce_workspace, tmpdir, test_type="main")


def test_p4_multiple_spaces_in_mappings(perforce_environment):
    perforce_environment.settings.PerforceWithMappings.project_depot_path = None
    perforce_environment.settings.PerforceWithMappings.mappings = [f"{perforce_environment.depot}   /..."]
    assert not __main__.run(perforce_environment.settings)


def test_p4_repository_difference_format(perforce_environment):
    p4 = perforce_environment.p4
    p4_file = perforce_environment.repo_file

    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="This is a changed step name", command=["ls", "-la"])])
"""
    p4.run_edit(perforce_environment.depot)
    p4_file.write(config)
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    settings = perforce_environment.settings
    settings.PerforceMainVcs.shelve_cls = [shelve_cl]
    settings.Launcher.config_path = p4_file.basename

    result = __main__.run(settings)

    assert result == 0
    diff = perforce_environment.temp_dir.join('artifacts', 'REPOSITORY_DIFFERENCE.txt').read()
    assert "This is a changed step name" in diff
    assert "b'" not in diff


@pytest.fixture()
def mock_opened(monkeypatch):
    def mocking_function(*args, **kwargs):
        raise P4.P4Exception("Client 'p4_disposable_workspace' unknown - use 'client' command to create it.")

    monkeypatch.setattr(P4.P4, 'run_opened', mocking_function, raising=False)


def test_p4_failed_opened(perforce_environment, mock_opened):
    assert not __main__.run(perforce_environment.settings)
