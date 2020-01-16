# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

from __future__ import absolute_import
import copy
import os
import shutil
import pytest
import six
from six.moves import range

import universum
from . import git_utils, perforce_utils, utils


def test_p4_success_command_line_poll_no_changes(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = universum.main(["poll", "-ot", "term",
                             "-vt", "p4",
                             "-f", six.text_type(db_file),
                             "-p4p", perforce_workspace.p4.port,
                             "-p4u", perforce_workspace.p4.user,
                             "-p4P", perforce_workspace.p4.password,
                             "-p4d", "//depot/...",
                             "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_git_success_command_line_poll_no_changes(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = universum.main(["poll", "-ot", "term",
                             "-vt", "git",
                             "-f", six.text_type(db_file),
                             "-gr", git_server.url,
                             "-grs", git_server.target_branch,
                             "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_vcs_error_no_vcs_type(capsys):
    try:
        del os.environ["VCS_TYPE"]
    except KeyError:
        pass
    with pytest.raises(SystemExit):
        universum.main(["-ot", "term"])

    assert "The repository (VCS) type is not set" in capsys.readouterr().err


def test_p4_error_command_line_wrong_port(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = universum.main(["poll", "-ot", "term",
                             "-vt", "p4",
                             "-f", six.text_type(db_file),
                             "-p4p", "127.0.0.1:1024",
                             "-p4u", perforce_workspace.p4.user,
                             "-p4P", perforce_workspace.p4.password,
                             "-p4d", "//depot/...",
                             "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("TCP connect to 127.0.0.1:1024 failed.")


def test_git_error_command_line_wrong_port(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = universum.main(["poll", "-ot", "term",
                             "-vt", "git",
                             "-f", six.text_type(db_file),
                             "-gr", "file:///non-existing-directory",
                             "-grs", git_server.target_branch,
                             "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("Cmd('git') failed due to: exit code(128)")

# ----------------------------------------------------------------------------------------------


class PollerParameters:
    def __init__(self, log_exception_checker, stdout_checker, http_check, environment):
        self.log_exception_checker = log_exception_checker
        self.stdout_checker = stdout_checker
        self.http_check = http_check
        self.poll_settings = environment.settings
        self.environment = environment

    def make_a_change(self):
        return self.environment.make_a_change()


@pytest.fixture()
def poll_parameters(log_exception_checker, stdout_checker, http_check):
    def inner(environment):
        return PollerParameters(log_exception_checker, stdout_checker, http_check, environment)
    yield inner


@pytest.fixture(params=["git", "p4"])
def poll_environment(request, perforce_workspace, git_client, tmpdir):
    if request.param == "git":
        yield git_utils.GitEnvironment(git_client, tmpdir, test_type="poll")
    else:
        yield perforce_utils.P4Environment(perforce_workspace, tmpdir, test_type="poll")


def test_poll_error_one_change(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    # make change in workspace
    change = parameters.make_a_change()

    # run poll again and fail triggering url because there is no server
    assert universum.run(parameters.poll_settings) != 0

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)

    # there is no listening server
    parameters.log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_poll_success_one_change(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    # make change in workspace
    change = parameters.make_a_change()

    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)
    parameters.http_check.assert_request_was_made({"cl": [change]})
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)


def test_poll_success_two_changes(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    # make changes in workspace
    change1 = parameters.make_a_change()
    change2 = parameters.make_a_change()

    # run poll again and trigger the url twice
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change1]})
    parameters.http_check.assert_request_was_made({"cl": [change2]})


def test_poll_changes_several_times(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    # make changes in workspace
    change1 = parameters.make_a_change()
    change2 = parameters.make_a_change()

    # run poll and trigger the urls
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change1]})
    parameters.http_check.assert_request_was_made({"cl": [change2]})

    # make more changes in workspace
    parameters.stdout_checker.reset()
    change3 = parameters.make_a_change()
    change4 = parameters.make_a_change()

    # run poll and trigger urls for the new changes only
    parameters.http_check.assert_success_and_collect(universum.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change3)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change4)
    parameters.stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change3]})
    parameters.http_check.assert_request_was_made({"cl": [change4]})
    parameters.http_check.assert_request_was_not_made({"cl": [change1]})
    parameters.http_check.assert_request_was_not_made({"cl": [change2]})

# ----------------------------------------------------------------------------------------------


def test_submit_error_no_repo(submit_environment, stdout_checker):
    settings = copy.deepcopy(submit_environment.settings)
    if settings.Vcs.type == "git":
        settings.ProjectDirectory.project_root = "non_existing_repo"
        universum.run(settings)
        stdout_checker.assert_has_calls_with_param("No such directory")
    else:
        settings.PerforceSubmitVcs.client = "non_existing_client"
        universum.run(settings)
        stdout_checker.assert_has_calls_with_param("Workspace 'non_existing_client' doesn't exist!")


class SubmitterParameters:
    def __init__(self, stdout_checker, environment):
        self.stdout_checker = stdout_checker
        self.submit_settings = environment.settings
        self.environment = environment

    def submit_path_list(self, path_list, **kwargs):
        settings = copy.deepcopy(self.submit_settings)
        setattr(settings.Submit, "reconcile_list", path_list)

        if kwargs:
            for key in kwargs:
                setattr(settings.Submit, key, kwargs[key])

        return universum.run(settings)

    def assert_submit_success(self, path_list, **kwargs):
        result = self.submit_path_list(path_list, **kwargs)
        assert result == 0

        last_cl = self.environment.get_last_change()
        self.stdout_checker.assert_has_calls_with_param("==> Change " + last_cl + " submitted")

    def file_present(self, file_path):
        return self.environment.file_present(file_path)

    def text_in_file(self, text, file_path):
        return self.environment.text_in_file(text, file_path)


@pytest.fixture()
def submit_parameters(stdout_checker):
    def inner(environment):
        return SubmitterParameters(stdout_checker, environment)
    yield inner


@pytest.fixture(params=["git", "p4"])
def submit_environment(request, perforce_workspace, git_client, tmpdir):
    if request.param == "git":
        yield git_utils.GitEnvironment(git_client, tmpdir, test_type="submit")
    else:
        yield perforce_utils.P4Environment(perforce_workspace, tmpdir, test_type="submit")


def test_submit_success_no_changes(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)
    assert parameters.submit_path_list([]) == 0


def test_submit_success_commit_add_modify_remove_one_file(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = parameters.environment.vcs_cooking_dir.join(file_name)
    file_path = six.text_type(temp_file)

    # Add a file
    temp_file.write("This is a new file" + "\n")
    parameters.assert_submit_success([file_path])
    assert parameters.file_present(file_path)

    # Modify a file
    text = "This is a new line in the file"
    temp_file.write(text + "\n")
    parameters.assert_submit_success([file_path])
    assert parameters.text_in_file(text, file_path)

    # Delete a file
    temp_file.remove()
    parameters.assert_submit_success([file_path])
    assert not parameters.file_present(file_path)


def test_submit_success_ignore_new_and_deleted_while_edit_only(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    new_file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = parameters.environment.vcs_cooking_dir.join(new_file_name)
    temp_file.write("This is a new temp file" + "\n")
    deleted_file_path = six.text_type(parameters.environment.repo_file)
    deleted_file_name = os.path.basename(deleted_file_path)
    os.remove(deleted_file_path)

    result = parameters.submit_path_list([six.text_type(temp_file), deleted_file_path], edit_only=True)
    assert result == 0

    parameters.stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(new_file_name))
    parameters.stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(deleted_file_name))
    parameters.stdout_checker.assert_has_calls_with_param("Nothing to submit")
    assert parameters.file_present(deleted_file_path)
    assert not parameters.file_present(six.text_type(temp_file))


def test_submit_success_commit_modified_while_edit_only(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    target_file = parameters.environment.repo_file
    text = utils.randomize_name("This is change ")
    target_file.write(text + "\n")

    parameters.assert_submit_success([six.text_type(target_file)], edit_only=True)
    assert parameters.text_in_file(text, six.text_type(target_file))


def test_submit_error_review(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    target_file = parameters.environment.repo_file
    target_file.write("This is some change")

    result = parameters.submit_path_list([six.text_type(target_file)], review=True)
    assert result != 0
    parameters.stdout_checker.assert_has_calls_with_param("not supported")


def test_submit_success_reconcile_directory(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    dir_name = utils.randomize_name("new_directory")

    # Create and reconcile new directory
    tmp_dir = parameters.environment.vcs_cooking_dir.mkdir(dir_name)
    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/"])

    for i in range(0, 9):
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        assert parameters.file_present(six.text_type(file_path))

    # Create and reconcile a directory in a directory
    another_dir = tmp_dir.mkdir("another_directory")
    tmp_file = another_dir.join("new_file.txt")
    tmp_file.write("This is some file" + "\n")

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/"])
    assert parameters.file_present(six.text_type(tmp_file))

    # Modify some vcs
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/"], edit_only=True)

    for i in range(0, 9, 2):
        file_path = tmp_dir.join("/new_file{}.txt".format(i))
        assert parameters.text_in_file(text, six.text_type(file_path))

    # Delete a directory
    shutil.rmtree(six.text_type(tmp_dir))
    parameters.assert_submit_success([six.text_type(tmp_dir)])
    assert not parameters.file_present(six.text_type(tmp_dir))


def test_submit_success_reconcile_wildcard(submit_parameters, submit_environment):
    parameters = submit_parameters(submit_environment)

    dir_name = utils.randomize_name("new_directory")

    # Create embedded directories, partially reconcile
    tmp_dir = parameters.environment.vcs_cooking_dir.mkdir(dir_name)
    inner_dir = tmp_dir.mkdir("inner_directory")
    text = "This is some file" + "\n"
    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/new_file*.txt"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert parameters.file_present(six.text_type(file_path))
        file_path = inner_dir.join(file_name)
        assert not parameters.file_present(six.text_type(file_path))
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert not parameters.file_present(six.text_type(file_path))

    # Create one more directory
    other_dir_name = utils.randomize_name("new_directory")
    other_tmp_dir = parameters.environment.vcs_cooking_dir.mkdir(other_dir_name)
    for i in range(0, 9):
        tmp_file = other_tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    parameters.assert_submit_success([six.text_type(parameters.environment.vcs_cooking_dir) + "/new_directory*/"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = other_tmp_dir.join(file_name)
        assert parameters.file_present(six.text_type(file_path))
        file_path = inner_dir.join(file_name)
        assert parameters.file_present(six.text_type(file_path))
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert parameters.file_present(six.text_type(file_path))

    # Modify some vcs
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/new_file*.txt"], edit_only=True)

    for i in range(0, 9, 2):
        file_path = tmp_dir.join("/new_file{}.txt".format(i))
        assert parameters.text_in_file(text, six.text_type(file_path))
        file_path = inner_dir.join("/new_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))
        file_path = tmp_dir.join("/another_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))

    # Test subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(1, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    parameters.assert_submit_success([six.text_type(tmp_dir) + "/*/*.txt"])

    for i in range(1, 9, 2):
        file_path = inner_dir.join("new_file{}.txt".format(i))
        assert parameters.text_in_file(text, six.text_type(file_path))
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))
        file_path = tmp_dir.join("another_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))

    # Test edit-only subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 3):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

        parameters.assert_submit_success([six.text_type(tmp_dir) + "/*/*.txt"], edit_only=True)

    for i in range(0, 9, 3):
        file_path = inner_dir.join("new_file{}.txt".format(i))
        assert parameters.text_in_file(text, six.text_type(file_path))
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))
        file_path = tmp_dir.join("another_file{}.txt".format(i))
        assert not parameters.text_in_file(text, six.text_type(file_path))

    # Clean up the repo
    shutil.rmtree(six.text_type(tmp_dir))
    shutil.rmtree(six.text_type(other_tmp_dir))
    parameters.assert_submit_success([six.text_type(parameters.environment.vcs_cooking_dir) + "/*"])
    assert not parameters.file_present(six.text_type(tmp_dir))
    assert not parameters.file_present(six.text_type(other_tmp_dir))
