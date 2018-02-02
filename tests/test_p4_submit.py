#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import os
import shutil
from P4 import P4Exception

import submit
from . import utils


def submit_path_list(workspace, path_list, additional_options=None):
    options = ["-ot", "term",
               "-vt", "p4",
               "-cm", "Test CL",
               "-p4p", workspace.p4.port,
               "-p4u", workspace.p4.user,
               "-p4P", workspace.p4.password,
               "-p4c", workspace.client_name]

    for path in path_list:
        options.extend(["-rl", path])
    if additional_options:
        options.extend(additional_options)

    return submit.main(options)


def ensure_submit_success(checker, workspace, path_list, additional_options=None):

    result = submit_path_list(workspace, path_list, additional_options)
    assert result == 0

    changes = workspace.p4.run_changes("-s", "submitted", "-m1", workspace.depot)
    last_cl = changes[0]["change"]
    checker.assert_has_calls_with_param("==> Change " + last_cl + " submitted")


def ensure_file_absent(file_path, workspace):
    try:
        workspace.p4.run_files("-e", file_path)
        assert False, "File '{}' is present in repository!".format(file_path)
    except P4Exception as e:
        if not e.warnings:
            raise
        if "no such file(s)" not in e.warnings[0]:
            raise


def test_success_commit_add_modify_remove_one_file(stdout_checker, perforce_workspace):
    file_name = utils.randomize_name("new_file") + ".txt"
    file_path = os.path.join(unicode(perforce_workspace.workspace_root), file_name)

    # Add a file
    temp_file = open(file_path, "ab")
    temp_file.write("This is a new file" + "\n")
    temp_file.close()
    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(file_path)])
    perforce_workspace.p4.run_files("-e", file_path)

    # Modify a file
    os.chmod(file_path, 0o777)
    temp_file = open(file_path, "ab")
    text = "This is a new line in the file"
    temp_file.write(text + "\n")
    temp_file.close()
    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(file_path)])
    assert text in perforce_workspace.p4.run_print(file_path)[-1]

    # Delete a file
    os.remove(file_path)
    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(file_path)])
    ensure_file_absent(file_path, perforce_workspace)


def test_success_ignore_new_and_deleted_while_edit_only(stdout_checker, perforce_workspace):
    new_file_name = utils.randomize_name("new_file") + ".txt"
    temp_file = perforce_workspace.workspace_root.join(new_file_name)
    temp_file.write("This is a new temp file" + "\n")
    deleted_file_path = unicode(perforce_workspace.workspace_file)
    deleted_file_name = os.path.basename(deleted_file_path)
    os.remove(deleted_file_path)

    result = submit_path_list(perforce_workspace, [unicode(temp_file), deleted_file_path], ["--edit-only"])
    assert result == 0

    stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(new_file_name))
    stdout_checker.assert_has_calls_with_param("Skipping '{}'".format(deleted_file_name))
    stdout_checker.assert_has_calls_with_param("Nothing to submit")
    perforce_workspace.p4.run_files("-e", deleted_file_path)
    ensure_file_absent(unicode(temp_file), perforce_workspace)


def test_success_commit_modified_while_edit_only(stdout_checker, perforce_workspace):
    target_file = perforce_workspace.workspace_file
    target_file.chmod(0o777)
    text = utils.randomize_name("This is change ")
    target_file.write(text + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(target_file)], ["--edit-only"])
    assert text in perforce_workspace.p4.run_print(unicode(target_file))[-1]


def test_error_review(stdout_checker, perforce_workspace):
    target_file = perforce_workspace.workspace_file
    target_file.chmod(0o777)
    target_file.write("This is some change")

    result = submit_path_list(perforce_workspace, [unicode(target_file)], ["--create-review"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("not supported")


def test_success_reconcile_directory(stdout_checker, perforce_workspace):
    dir_name = utils.randomize_name("new_directory")

    # Create and reconcile new directory
    tmp_dir = perforce_workspace.workspace_root.mkdir(dir_name)
    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir)])

    for i in range(0, 9):
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        perforce_workspace.p4.run_files("-e", file_path)

    # Create and reconcile a directory in a directory
    another_dir = tmp_dir.mkdir("another_directory")
    tmp_file = another_dir.join("new_file.txt")
    tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir)])
    perforce_workspace.p4.run_files(unicode(tmp_file))

    # Modify some files
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir)], ["--edit-only"])

    for i in range(0, 9, 2):
        file_path = tmp_dir.join("/new_file{}.txt".format(i))
        assert text in perforce_workspace.p4.run_print(unicode(file_path))[-1]

    # Delete a directory
    shutil.rmtree(unicode(tmp_dir))
    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir)])
    ensure_file_absent(unicode(tmp_dir), perforce_workspace)


def test_success_reconcile_wildcard(stdout_checker, perforce_workspace):
    dir_name = utils.randomize_name("new_directory")

    # Create embedded directories, partially reconcile
    tmp_dir = perforce_workspace.workspace_root.mkdir(dir_name)
    inner_dir = tmp_dir.mkdir("inner_directory")
    text = "This is some file" + "\n"
    for i in range(0, 9):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.write(text)
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.write(text)

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir) + "/new_file*.txt"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        perforce_workspace.p4.run_files("-e", file_path)
        file_path = inner_dir.join(file_name)
        ensure_file_absent(file_path, perforce_workspace)
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        ensure_file_absent(file_path, perforce_workspace)

    # Create one more directory
    other_dir_name = utils.randomize_name("new_directory")
    other_tmp_dir = perforce_workspace.workspace_root.mkdir(other_dir_name)
    for i in range(0, 9):
        tmp_file = other_tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.write("This is some file" + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace,
                          [unicode(perforce_workspace.workspace_root) + "/new_directory*"])

    for i in range(0, 9):
        file_name = "new_file{}.txt".format(i)
        file_path = other_tmp_dir.join(file_name)
        perforce_workspace.p4.run_files("-e", file_path)
        file_path = inner_dir.join(file_name)
        perforce_workspace.p4.run_files("-e", file_path)
        file_name = "another_file{}.txt".format(i)
        file_path = tmp_dir.join(file_name)
        perforce_workspace.p4.run_files("-e", file_path)

    # Modify some files
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir) + "/new_file*.txt"], ["--edit-only"])

    for i in range(0, 9, 2):
        file_path = tmp_dir.join("/new_file{}.txt".format(i))
        assert text in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = inner_dir.join("/new_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = tmp_dir.join("/another_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]

    # Test subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(1, 9, 2):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir) + "/*/*.txt"])

    for i in range(1, 9, 2):
        file_path = inner_dir.join("new_file{}.txt".format(i))
        assert text in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = tmp_dir.join("another_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]

    # Test edit-only subdirectory wildcard
    text = utils.randomize_name("This is change ")
    for i in range(0, 9, 3):
        tmp_file = tmp_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = inner_dir.join("new_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")
        tmp_file = tmp_dir.join("another_file{}.txt".format(i))
        tmp_file.chmod(0o777)
        tmp_file.write(text + "\n")

    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(tmp_dir) + "/*/*.txt"], ["--edit-only"])

    for i in range(0, 9, 3):
        file_path = inner_dir.join("new_file{}.txt".format(i))
        assert text in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = tmp_dir.join("new_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]
        file_path = tmp_dir.join("another_file{}.txt".format(i))
        assert text not in perforce_workspace.p4.run_print(unicode(file_path))[-1]

    # Clean up the repo
    shutil.rmtree(unicode(tmp_dir))
    shutil.rmtree(unicode(other_tmp_dir))
    ensure_submit_success(stdout_checker, perforce_workspace, [unicode(perforce_workspace.workspace_root) + "/*"])
    ensure_file_absent(unicode(tmp_dir), perforce_workspace)
    ensure_file_absent(unicode(other_tmp_dir), perforce_workspace)
