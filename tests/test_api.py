#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import json
import os
import pytest
import six
from six.moves import range


config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run script", artifacts="output.json",
                           command=["bash", "-c", "universum api file-diff > output.json"])])
"""


@pytest.mark.nonci_applicable
def test_error_wrong_environment(universum_runner):
    log = universum_runner.environment.assert_unsuccessful_execution("universum api file-diff")
    assert "Error: Failed to read the 'UNIVERSUM_DATA_FILE' from environment" in log


def test_p4_file_diff(universum_runner):
    p4 = universum_runner.perforce.p4
    p4_directory = universum_runner.perforce.root_directory
    p4_file = universum_runner.perforce.repo_file

    p4.run_edit(six.text_type(p4_file))
    p4_file.write("This line is added to the file.\n")
    p4.run_move(six.text_type(p4_file), six.text_type(p4_directory.join("some_new_file_name.txt")))
    change = p4.fetch_change()
    change["Description"] = "Rename basic config"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    log = universum_runner.run(config, vcs_type="p4",
                               environment=["SHELVE_CHANGELIST=" + shelve_cl],
                               additional_parameters=" --p4-force-clean")
    assert "Module sh got exit code" not in log

    with open(os.path.join(universum_runner.artifact_dir, "output.json")) as f:
        result = json.load(f)

    assert result[0]["action"] == "move/add"
    assert result[0]["repo_path"] == "//depot/some_new_file_name.txt"
    assert result[1]["action"] == "move/delete"
    assert result[1]["repo_path"] == "//depot/writeable_file.txt"


def test_multiple_p4_file_diff(universum_runner):
    p4 = universum_runner.perforce.p4
    p4_directory = universum_runner.perforce.root_directory

    for index in range(0, 10000):
        new_file = p4_directory.join("new_file_" + six.text_type(index) + ".txt")
        new_file.write("This is file #" + six.text_type(index) + "\n")
        p4.run_add(six.text_type(new_file))
    change = p4.fetch_change()
    change["Description"] = "Add 10000 files"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    log = universum_runner.run(config, vcs_type="p4",
                               environment=["SHELVE_CHANGELIST=" + shelve_cl],
                               additional_parameters=" --p4-force-clean")
    assert "Module sh got exit code" not in log

    with open(os.path.join(universum_runner.artifact_dir, "output.json")) as f:
        result = json.load(f)
    assert len(result) == 10000
    for entry in result:
        assert entry["action"] == "add"


def test_git_file_diff(universum_runner):
    repo = universum_runner.git.repo
    server = universum_runner.git.server
    logger = universum_runner.git.logger
    git_directory = universum_runner.git.root_directory
    git_file = universum_runner.git.repo_file

    repo.git.checkout(server.target_branch)
    repo.git.checkout("new_testing_branch", b=True)
    repo.git.mv(six.text_type(git_file), six.text_type(git_directory.join("some_new_file_name.txt")))
    change = six.text_type(repo.index.commit("Special commit for testing"))
    repo.remotes.origin.push(progress=logger, all=True)

    log = universum_runner.run(config, vcs_type="git",
                               environment=["GIT_CHERRYPICK_ID=" + change, "GIT_REFSPEC=" + server.target_branch])
    assert "Module sh got exit code" not in log

    with open(os.path.join(universum_runner.artifact_dir, "output.json")) as f:
        result = json.load(f)

    assert result[0]["action"] == "delete"
    assert result[0]["repo_path"] == "readme.txt"
    assert result[1]["action"] == "add"
    assert result[1]["repo_path"] == "some_new_file_name.txt"


def test_multiple_git_file_diff(universum_runner):
    repo = universum_runner.git.repo
    server = universum_runner.git.server
    logger = universum_runner.git.logger
    git_directory = universum_runner.git.root_directory

    repo.git.checkout(server.target_branch)
    repo.git.checkout("new_testing_branch", b=True)
    files = []
    for index in range(0, 10000):
        new_file = git_directory.join("new_file_" + six.text_type(index) + ".txt")
        new_file.write("This is file #" + six.text_type(index) + "\n")
        files.append(six.text_type(new_file))
    repo.index.add(files)
    change = six.text_type(repo.index.commit("Special commit for testing"))
    repo.remotes.origin.push(progress=logger, all=True)

    log = universum_runner.run(config, vcs_type="git",
                               environment=["GIT_CHERRYPICK_ID=" + change, "GIT_REFSPEC=" + server.target_branch])
    assert "Module sh got exit code" not in log

    with open(os.path.join(universum_runner.artifact_dir, "output.json")) as f:
        result = json.load(f)
    assert len(result) == 10000
    for entry in result:
        assert entry["action"] == "add"
