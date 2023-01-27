# pylint: disable = redefined-outer-name

import os
from typing import Callable, Union
import shutil
import pathlib
import pytest

from . import utils
from .conftest import FuzzyCallChecker
from .git_utils import GitTestEnvironment, GitClient
from .perforce_utils import P4TestEnvironment, PerforceWorkspace


@pytest.fixture()
def p4_submit_environment(perforce_workspace: PerforceWorkspace, tmp_path: pathlib.Path):
    yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="submit")


@pytest.mark.parametrize("branch", ["write-protected", "trigger-protected"])
def test_p4_error_forbidden_branch(p4_submit_environment: P4TestEnvironment, branch: str):
    protected_dir = p4_submit_environment.vcs_client.root_directory / branch
    protected_dir.mkdir()
    file_name = utils.randomize_name("new_file") + ".txt"
    file_to_add = protected_dir / file_name
    text = "This is a new line in the file"
    file_to_add.write_text(text + "\n")

    p4_submit_environment.settings.Submit.reconcile_list = str(file_to_add)

    p4_submit_environment.run(expect_failure=True)

    p4 = p4_submit_environment.vcs_client.p4
    # make sure submitter didn't leave any pending CLs in the workspace
    assert not p4.run_changes("-c", p4_submit_environment.client_name, "-s", "pending")
    # make sure submitter didn't leave any pending changes in default CL
    assert not p4.run_opened("-C", p4_submit_environment.client_name)


def test_p4_success_files_in_default(p4_submit_environment: P4TestEnvironment):
    # This file should not be submitted, it should remain unchanged in default CL
    p4 = p4_submit_environment.vcs_client.p4
    p4_file = p4_submit_environment.vcs_client.repo_file
    p4.run_edit(str(p4_file))
    text = "This text should be in file"
    p4_file.write_text(text + "\n")

    # This file should be successfully submitted
    file_name = utils.randomize_name("new_file") + ".txt"
    new_file = p4_submit_environment.vcs_client.root_directory / file_name
    new_file.write_text("This is a new file" + "\n")

    p4_submit_environment.settings.Submit.reconcile_list = str(new_file)

    p4_submit_environment.run()
    assert text in p4_file.read_text()


def test_p4_error_files_in_default_and_reverted(p4_submit_environment: P4TestEnvironment):
    # This file should not be submitted, it should remain unchanged in default CL
    p4 = p4_submit_environment.vcs_client.p4
    p4_file = p4_submit_environment.vcs_client.repo_file
    p4.run_edit(str(p4_file))
    text_default = "This text should be in file"
    p4_file.write_text(text_default + "\n")

    # This file must fail submit and remain unchanged while not checked out any more
    protected_dir = p4_submit_environment.vcs_client.root_directory / "write-protected"
    protected_dir.mkdir()
    file_name = utils.randomize_name("new_file") + ".txt"
    new_file = protected_dir / file_name
    text_new = "This is a new line in the file"
    new_file.write_text(text_new + "\n")

    p4_submit_environment.settings.Submit.reconcile_list = str(new_file)

    p4_submit_environment.run(expect_failure=True)
    assert text_default in p4_file.read_text()
    assert text_new in new_file.read_text()


class SubmitterParameters:
    def __init__(self, stdout_checker: FuzzyCallChecker, environment: Union[GitTestEnvironment, P4TestEnvironment]):
        self.stdout_checker: FuzzyCallChecker = stdout_checker
        self.environment: Union[GitTestEnvironment, P4TestEnvironment] = environment

    def submit_path_list(self, path_list, expect_failure=False, **kwargs):
        self.environment.settings.Submit.reconcile_list = ",".join(path_list)

        if kwargs:
            for key, value in kwargs.items():
                setattr(self.environment.settings.Submit, key, value)

        self.environment.run(expect_failure=expect_failure)

    def assert_submit_success(self, path_list, **kwargs):
        self.submit_path_list(path_list, **kwargs)

        last_cl = self.environment.vcs_client.get_last_change()
        self.stdout_checker.assert_has_calls_with_param("==> Change " + last_cl + " submitted")

    def file_present(self, file_path):
        return self.environment.vcs_client.file_present(file_path)

    def text_in_file(self, text, file_path):
        return self.environment.vcs_client.text_in_file(text, file_path)


@pytest.fixture()
def submit_parameters(stdout_checker: FuzzyCallChecker):
    def inner(environment):
        return SubmitterParameters(stdout_checker, environment)
    yield inner


@pytest.fixture(params=["git", "p4"])
def submit_environment(request, perforce_workspace: PerforceWorkspace, git_client: GitClient, tmp_path: pathlib.Path):
    if request.param == "git":
        yield GitTestEnvironment(git_client, tmp_path, test_type="submit")
    else:
        yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="submit")


def test_error_no_repo(submit_environment: Union[GitTestEnvironment, P4TestEnvironment], stdout_checker: FuzzyCallChecker):
    if submit_environment.settings.Vcs.type == "git":
        submit_environment.settings.ProjectDirectory.project_root = "non_existing_repo"
        submit_environment.run(expect_failure=True)
        stdout_checker.assert_has_calls_with_param("No such directory")
    else:
        submit_environment.settings.PerforceSubmitVcs.client = "non_existing_client"
        submit_environment.run(expect_failure=True)
        stdout_checker.assert_has_calls_with_param("Workspace 'non_existing_client' doesn't exist!")


def test_success_no_changes(submit_parameters: Callable, submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)
    parameters.submit_path_list([])


def test_success_commit_add_modify_remove_one_file(submit_parameters: Callable,
                                                   submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = parameters.environment.vcs_client.root_directory / file_name
    file_path = str(temp_file)

    # Add a file
    temp_file.write_text("This is a new file" + "\n")
    parameters.assert_submit_success([file_path])
    assert parameters.file_present(file_path)

    # Modify a file
    text = "This is a new line in the file"
    temp_file.write_text(text + "\n")
    parameters.assert_submit_success([file_path])
    assert parameters.text_in_file(text, file_path)

    # Delete a file
    temp_file.unlink()
    parameters.assert_submit_success([file_path])
    assert not parameters.file_present(file_path)


def test_success_ignore_new_and_deleted_while_edit_only(submit_parameters: Callable,
                                                        submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    new_file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = parameters.environment.vcs_client.root_directory / new_file_name
    temp_file.write_text("This is a new temp file" + "\n")
    deleted_file_path = str(parameters.environment.vcs_client.repo_file)
    deleted_file_name = os.path.basename(deleted_file_path)
    os.remove(deleted_file_path)

    parameters.submit_path_list([str(temp_file), deleted_file_path], edit_only=True)

    parameters.stdout_checker.assert_has_calls_with_param(f"Skipping '{new_file_name}'")
    parameters.stdout_checker.assert_has_calls_with_param(f"Skipping '{deleted_file_name}'")
    parameters.stdout_checker.assert_has_calls_with_param("Nothing to submit")
    assert parameters.file_present(deleted_file_path)
    assert not parameters.file_present(str(temp_file))


def test_success_commit_modified_while_edit_only(submit_parameters: Callable,
                                                 submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    target_file = parameters.environment.vcs_client.repo_file
    text = utils.randomize_name("This is change ")
    target_file.write_text(text + "\n")

    parameters.assert_submit_success([str(target_file)], edit_only=True)
    assert parameters.text_in_file(text, str(target_file))


def test_error_review(submit_parameters: Callable, submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    target_file = parameters.environment.vcs_client.repo_file
    target_file.write_text("This is some change")

    parameters.submit_path_list([str(target_file)], review=True, expect_failure=True)
    parameters.stdout_checker.assert_has_calls_with_param("not supported")


def test_success_reconcile_directory(submit_parameters: Callable,
                                     submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    dir_name = utils.randomize_name("new_directory")

    # Create and reconcile new directory
    tmp_dir = parameters.environment.vcs_client.root_directory / dir_name
    tmp_dir.mkdir()
    for i in range(0, 9):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text("This is some file" + "\n")

    parameters.assert_submit_success([str(tmp_dir) + "/"])

    for i in range(0, 9):
        file_path = tmp_dir / f"new_file{i}.txt"
        assert parameters.file_present(str(file_path))

    # Create and reconcile a directory in a directory
    another_dir = tmp_dir / "another_directory"
    another_dir.mkdir()
    tmp_file = another_dir / "new_file.txt"
    tmp_file.write_text("This is some file" + "\n")

    parameters.assert_submit_success([str(tmp_dir) + "/"])
    assert parameters.file_present(str(tmp_file))

    # Modify some vcs
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")

    parameters.assert_submit_success([str(tmp_dir) + "/"], edit_only=True)

    for i in range(0, 9, 2):
        file_path = tmp_dir / f"new_file{i}.txt"
        assert parameters.text_in_file(text, str(file_path))
    parameters.environment.settings.Submit.edit_only = False

    # Delete a directory
    shutil.rmtree(tmp_dir)
    parameters.assert_submit_success([str(tmp_dir)])
    assert not parameters.file_present(str(tmp_dir))


def test_success_reconcile_wildcard(submit_parameters: Callable,
                                    submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    parameters = submit_parameters(submit_environment)

    dir_name = utils.randomize_name("new_directory")

    # Create embedded directories, partially reconcile
    tmp_dir = parameters.environment.vcs_client.root_directory / dir_name
    tmp_dir.mkdir()
    inner_dir = tmp_dir / "inner_directory"
    inner_dir.mkdir()
    text = "This is some file" + "\n"
    for i in range(0, 9):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text(text)
        tmp_file = tmp_dir / f"another_file{i}.txt"
        tmp_file.write_text(text)
        tmp_file = inner_dir / f"new_file{i}.txt"
        tmp_file.write_text(text)

    parameters.assert_submit_success([str(tmp_dir) + "/new_file*.txt"])

    for i in range(0, 9):
        file_name = f"new_file{i}.txt"
        file_path = tmp_dir / file_name
        assert parameters.file_present(str(file_path))
        file_path = inner_dir / file_name
        assert not parameters.file_present(str(file_path))
        file_name = f"another_file{i}.txt"
        file_path = tmp_dir / file_name
        assert not parameters.file_present(str(file_path))

    # Create one more directory
    other_dir_name = utils.randomize_name("new_directory")
    other_tmp_dir = parameters.environment.vcs_client.root_directory / other_dir_name
    other_tmp_dir.mkdir()
    for i in range(0, 9):
        tmp_file = other_tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text("This is some file" + "\n")

    parameters.assert_submit_success([str(parameters.environment.vcs_client.root_directory) + "/new_directory*/"])

    for i in range(0, 9):
        file_name = f"new_file{i}.txt"
        file_path = other_tmp_dir / file_name
        assert parameters.file_present(str(file_path))
        file_path = inner_dir / file_name
        assert parameters.file_present(str(file_path))
        file_name = f"another_file{i}.txt"
        file_path = tmp_dir / file_name
        assert parameters.file_present(str(file_path))

    # Modify some vcs
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = inner_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = tmp_dir / f"another_file{i}.txt"
        tmp_file.write_text(text + "\n")

    parameters.assert_submit_success([str(tmp_dir) + "/new_file*.txt"], edit_only=True)

    for i in range(0, 9, 2):
        file_path = tmp_dir / f"new_file{i}.txt"
        assert parameters.text_in_file(text, str(file_path))
        file_path = inner_dir / f"new_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))
        file_path = tmp_dir / f"another_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))

    # Test subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(1, 9, 2):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = inner_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = tmp_dir / f"another_file{i}.txt"
        tmp_file.write_text(text + "\n")

    parameters.assert_submit_success([str(tmp_dir) + "/*/*.txt"])

    for i in range(1, 9, 2):
        file_path = inner_dir / f"new_file{i}.txt"
        assert parameters.text_in_file(text, str(file_path))
        file_path = tmp_dir / f"new_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))
        file_path = tmp_dir / f"another_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))

    # Test edit-only subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 3):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = inner_dir / f"new_file{i}.txt"
        tmp_file.write_text(text + "\n")
        tmp_file = tmp_dir / "another_file{i}.txt"
        tmp_file.write_text(text + "\n")

        parameters.assert_submit_success([str(tmp_dir) + "/*/*.txt"], edit_only=True)

    for i in range(0, 9, 3):
        file_path = inner_dir / f"new_file{i}.txt"
        assert parameters.text_in_file(text, str(file_path))
        file_path = tmp_dir / f"new_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))
        file_path = tmp_dir / f"another_file{i}.txt"
        assert not parameters.text_in_file(text, str(file_path))
    parameters.environment.settings.Submit.edit_only = False

    # Clean up the repo
    shutil.rmtree(str(tmp_dir))
    shutil.rmtree(str(other_tmp_dir))
    parameters.assert_submit_success([str(parameters.environment.vcs_client.root_directory) + "/*"])
    assert not parameters.file_present(str(tmp_dir))
    assert not parameters.file_present(str(other_tmp_dir))


def test_success_reconcile_partial(submit_parameters: Callable,
                                   submit_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    # This test was failed when a bug in univesrum.lib.utils.unify_argument_list left empty entries in processed lists
    # When reconciling "", p4 adds to CL all changes made in scope of workspace (and therefore partial reconcile fails)

    parameters = submit_parameters(submit_environment)
    dir_name = utils.randomize_name("new_directory")
    tmp_dir = parameters.environment.vcs_client.root_directory / dir_name
    tmp_dir.mkdir()
    for i in range(0, 9):
        tmp_file = tmp_dir / f"new_file{i}.txt"
        tmp_file.write_text("This is some file" + "\n")

    reconcile_list = [str(tmp_dir / f"new_file{i}.txt") for i in range(0, 4)]
    reconcile_list.extend(["", " ", "\n"])
    parameters.assert_submit_success(reconcile_list)

    for i in range(0, 4):
        file_path = tmp_dir / f"new_file{i}.txt"
        assert parameters.file_present(str(file_path))

    for i in range(5, 9):
        file_path = tmp_dir / f"new_file{i}.txt"
        assert not parameters.file_present(str(file_path))

    # Delete a directory
    shutil.rmtree(tmp_dir)
    parameters.assert_submit_success([str(tmp_dir)])
    assert not parameters.file_present(str(tmp_dir))
