import pytest

from universum import __main__
from . import utils


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
from universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["bash", "-c", "rm -rf {}"])])
""".format(env.settings.ProjectDirectory.project_root))

    __main__.run(env.settings)
    # the log output is automatically checked by the 'detect_fails' fixture


def test_p4_multiple_spaces_in_mappings(perforce_workspace, tmpdir):
    environment = utils.TestEnvironment(tmpdir, "main")
    environment.settings.Vcs.type = "p4"
    environment.settings.PerforceVcs.port = perforce_workspace.p4.port
    environment.settings.PerforceVcs.user = perforce_workspace.p4.user
    environment.settings.PerforceVcs.password = perforce_workspace.p4.password
    environment.settings.PerforceMainVcs.client = "regression_disposable_workspace"
    environment.settings.PerforceMainVcs.force_clean = True
    environment.settings.PerforceWithMappings.mappings = [f"{perforce_workspace.depot}   /..."]
    assert not __main__.run(environment.settings)


def test_non_utf8_environment(docker_main):
    output = docker_main.run("""
from universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="none", environment=['LANG=POSIX', 'LC_ALL=POSIX'])
    assert "\u2514" in output

    docker_main.clean_artifacts()
    docker_main.environment.assert_successful_execution('apt install -y locales')
    docker_main.environment.assert_successful_execution('locale-gen --purge en_US')
    docker_main.environment.assert_successful_execution('update-locale LANG=en_US')
    output = docker_main.run("""
from universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="none", environment=['LANG=en_US', 'LC_ALL=en_US'])
    assert "\u2514" not in output
