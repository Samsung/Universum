import pathlib

import P4
import pytest
from tests import utils
from tests.conftest import FuzzyCallChecker
from tests.perforce_utils import PerforceWorkspace, P4TestEnvironment
from tests.utils import python


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


def test_p4_delete_file_in_shelve(perforce_environment: P4TestEnvironment):
    p4 = perforce_environment.vcs_client.p4
    test_dir = perforce_environment.vcs_client.root_directory / "delete_test_files"
    test_dir.mkdir(exist_ok=True)

    # Create a file and submit it to the depot
    file_to_delete = test_dir / "file_to_delete"
    p4.run("add", str(file_to_delete))
    p4.run("edit", str(file_to_delete))
    file_to_delete.write_text("This file will be deleted in a shelve.\n")

    change = p4.run_change("-o")[0]
    change["Description"] = "Submit file for delete test"
    p4.run_submit(change)

    # Create a changelist and shelve the deleting
    p4.run("delete", str(file_to_delete))
    change = p4.fetch_change()
    change["Description"] = "Test delete in shelve"
    saved_change = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", saved_change)

    # Submit a modification to the file after the shelve was created
    # This ensures the unshelve will try to delete an earlier version of the file
    p4.run_revert(str(file_to_delete))
    p4.run("edit", str(file_to_delete))
    file_to_delete.write_text("This file was modified after the shelve.\n")
    change = p4.run_change("-o")[0]
    change["Description"] = "Modify file after shelve"
    p4.run_submit(change)

    perforce_environment.settings.PerforceMainVcs.shelve_cls = [saved_change]
    perforce_environment.run()

    # Verify the diff shows the file was deleted
    diff_file = perforce_environment.artifact_dir / 'REPOSITORY_DIFFERENCE.txt'
    assert diff_file.exists(), "REPOSITORY_DIFFERENCE.txt should exist for deleted file in shelve"
    diff_content = diff_file.read_text()
    assert "open for read" in diff_content, "We expect an error message in diff file"
