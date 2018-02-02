#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import os
import shutil

import git
import pytest

import submit
from . import utils


class GitClient(object):
    def __init__(self, workdir, server):
        self.server = server

        self.workdir = workdir
        self.repo = git.Repo.clone_from(self.server.url, unicode(workdir))
        self.repo.git.checkout(self.server.target_branch)
        self.repo_file = self.workdir.join(self.server.target_file)


@pytest.fixture()
def git_client(tmpdir, git_server):
    directory = tmpdir.mkdir("client")
    yield GitClient(directory, git_server)


def submit_path_list(client, path_list, additional_options=None):
    options = ["-ot", "term",
               "-vt", "git",
               "-cm", "Test CL",
               "-gu", "Testing User",
               "-ge", "some@email.com",
               "-pr", unicode(client.workdir),
               "-gr", client.server.url,
               "-grs", client.server.target_branch]

    for path in path_list:
        options.extend(["-rl", path])

    if additional_options:
        options.extend(additional_options)

    return submit.main(options)


def ensure_submit_success(checker, client, path_list, additional_options=None):
    result = submit_path_list(client, path_list, additional_options)
    assert result == 0

    changes = client.repo.git.log("origin/" + client.server.target_branch, pretty="oneline", max_count=1)
    last_cl = changes.split(" ")[0]
    checker.assert_has_calls_with_param("==> Change " + last_cl + " submitted")


def test_success_commit_add_modify_remove_one_file(stdout_checker, git_client):
    file_name = utils.randomize_name("new_file") + ".txt"
    file_path = os.path.join(unicode(git_client.workdir), file_name)

    # Add a file
    temp_file = open(file_path, "ab")
    temp_file.write("This is a new file" + "\n")
    temp_file.close()
    ensure_submit_success(stdout_checker, git_client, [unicode(file_path)])
    assert file_name in git_client.repo.git.ls_files(file_path)

    # Modify a file
    temp_file = open(file_path, "ab")
    text = "This is a new line in the file"
    temp_file.write(text + "\n")
    temp_file.close()
    ensure_submit_success(stdout_checker, git_client, [unicode(file_path)])
    assert text in git_client.repo.git.show("HEAD:" + file_name)

    # Delete a file
    os.remove(file_path)
    ensure_submit_success(stdout_checker, git_client, [unicode(file_path)])
    assert file_name not in git_client.repo.git.ls_files(file_path)


def test_success_ignore_new_and_deleted_while_edit_only(stdout_checker, git_client):
    new_file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = git_client.workdir.join(new_file_name)
    temp_file.write("This is a new temp file" + "\n")
    deleted_file_path = unicode(git_client.repo_file)
    deleted_file_name = os.path.basename(deleted_file_path)
    os.remove(deleted_file_path)

    result = submit_path_list(git_client, [deleted_file_name, unicode(temp_file)], ["--edit-only"])
    assert result == 0

    stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(new_file_name))
    stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(deleted_file_name))
    stdout_checker.assert_has_calls_with_param("Nothing to submit")
    assert new_file_name not in git_client.repo.git.ls_files(unicode(temp_file))
    assert deleted_file_name in git_client.repo.git.ls_files(deleted_file_path)


def test_success_commit_modified_while_edit_only(stdout_checker, git_client):
    text = utils.randomize_name("This is change ")
    git_client.repo_file.write(text + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(git_client.repo_file)], ["--edit-only"])

    relative_path = os.path.relpath(unicode(git_client.repo_file), unicode(git_client.workdir))
    assert text in git_client.repo.git.show("HEAD:" + relative_path)


def test_error_review_no_gerrit(stdout_checker, git_client):
    git_client.repo_file.write("This is some change" + "\n")

    result = submit_path_list(git_client, [unicode(git_client.repo_file)], ["--create-review"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("not supported")


def test_success_reconcile_directory(stdout_checker, git_client):
    dir_name = utils.randomize_name("new_directory")

    # Create and reconcile new directory
    tmp_dir = git_client.workdir.mkdir(dir_name)
    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir)])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert file_name in git_client.repo.git.ls_files(file_path)

    # Create and reconcile a directory in a directory
    another_dir = tmp_dir.mkdir("another_directory")
    tmp_file = another_dir.join("new_file.txt")
    tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir)])

    relative_path = os.path.relpath(unicode(tmp_file), unicode(git_client.workdir))
    assert relative_path in git_client.repo.git.ls_files(tmp_file)

    # Modify some files
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir)], ["--edit-only"])

    for i in range(0, 9, 2):
        file_path = dir_name + "/new_file{}.txt".format(i)
        assert text in git_client.repo.git.show("HEAD:" + file_path)

    # Delete a directory
    shutil.rmtree(unicode(tmp_dir))
    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir)])
    assert not git_client.repo.git.ls_files(unicode(tmp_dir))


def test_success_reconcile_wildcard(stdout_checker, git_client):
    dir_name = utils.randomize_name("new_directory")

    # Create embedded directories, partially reconcile
    tmp_dir = git_client.workdir.mkdir(dir_name)
    inner_dir = tmp_dir.mkdir("inner_directory")
    text = "This is some file" + "\n"

    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text)

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir) + "/new_file*.txt"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert file_name in git_client.repo.git.ls_files(file_path)
        file_path = inner_dir.join(file_name)
        assert file_name not in git_client.repo.git.ls_files(file_path)
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert file_name not in git_client.repo.git.ls_files(file_path)

    # Create one more directory
    other_dir_name = utils.randomize_name("new_directory")
    other_tmp_dir = git_client.workdir.mkdir(other_dir_name)
    for i in range(0, 9):
        tmp_file = other_tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(git_client.workdir) + "/new_directory*"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = other_tmp_dir.join(file_name)
        assert file_name in git_client.repo.git.ls_files(file_path)
        file_path = inner_dir.join(file_name)
        assert file_name in git_client.repo.git.ls_files(file_path)
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        assert file_name in git_client.repo.git.ls_files(file_path)

    # Modify some files
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir) + "/new_file*.txt"], ["--edit-only"])

    for i in range(0, 9, 2):
        file_path = dir_name + "/new_file{}.txt".format(i)
        assert text in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/inner_directory/new_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/another_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)

    # Test subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(1, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir) + "/*/*.txt"])

    for i in range(1, 9, 2):
        file_path = dir_name + "/inner_directory/new_file{}.txt".format(i)
        assert text in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/new_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/another_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)

    # Test edit-only subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 3):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, git_client, [unicode(tmp_dir) + "/*/*.txt"], ["--edit-only"])

    for i in range(0, 9, 3):
        file_path = dir_name + "/inner_directory/new_file{}.txt".format(i)
        assert text in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/new_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)
        file_path = dir_name + "/another_file{}.txt".format(i)
        assert text not in git_client.repo.git.show("HEAD:" + file_path)

    # Clean up the repo
    shutil.rmtree(unicode(tmp_dir))
    shutil.rmtree(unicode(other_tmp_dir))
    ensure_submit_success(stdout_checker, git_client, [unicode(git_client.workdir) + "/*"])
    assert not git_client.repo.git.ls_files(unicode(tmp_dir))
    assert not git_client.repo.git.ls_files(unicode(other_tmp_dir))
