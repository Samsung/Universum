#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import pytest

import poll
from _universum import gravity
from . import default_args


def test_success_command_line_poll_no_changes(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = poll.main(["-ot", "term",
                        "-vt", "git",
                        "-f", unicode(db_file),
                        "-gr", git_server.url,
                        "-grs", git_server.target_branch,
                        "-u", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_error_command_line_wrong_port(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = poll.main(["-ot", "term",
                        "-vt", "git",
                        "-f", unicode(db_file),
                        "-gr", "file:///non-existing-directory",
                        "-grs", git_server.target_branch,
                        "-u", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("Cmd('git') failed due to: exit code(128)")


class GitPollSettings(object):
    def __init__(self, server, db_file):
        self.server = server

        argument_parser = default_args.ArgParserWithDefault()
        gravity.define_arguments_recursive(poll.Poller, argument_parser)

        self.settings = argument_parser.parse_args([])

        self.settings.Poller.db_file = unicode(db_file)
        self.settings.Output.type = "term"
        self.settings.FileManager.vcs = "git"
        self.settings.BasicServer.url = "https://localhost/?cl=%s"

        self.settings.GitVcs.repo = server.url
        self.settings.GitVcs.refspec = server.target_branch


@pytest.fixture()
def git_poll_settings(git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")

    yield GitPollSettings(git_server, db_file)


def make_branch_with_changes(git_server, branch_name, commits_number, branch_from=None):
    """
    Creates a branch from the current or specified (by name) and adds passed commits number.

    :param git_server: Reference to the instance of the GitServer class from the confest.py
    :param branch_name: Name of newly created branch
    :param commits_number: Number of commits to be made in created branch
    :param branch_from: Branch name to check out from. By default branch will be made from the current
    :return: A list of commits "hashes"
    """
    if branch_from:
        git_server.switch_branch(branch_from)
    git_server.make_branch(branch_name)
    commits = [git_server.commit_new_file() for _ in range(commits_number)]
    git_server.switch_branch(git_server.target_branch)
    return commits


def assert_polled_commits(commits, stdout_checker, http_request_checker):
    for commit in commits:
        stdout_checker.assert_has_calls_with_param("==> Detected commit " + commit)
        http_request_checker.assert_request_was_made({"cl": [commit]})


def test_error_one_change(log_exception_checker, stdout_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # make change in workspace
    change = git_poll_settings.server.make_a_change()

    # run poll again and fail triggering url because there is no server
    assert poll.run(git_poll_settings.settings) != 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)

    # there is no listening server
    log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_success_one_change(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # make change in workspace
    change = git_poll_settings.server.make_a_change()

    # run poll again and trigger the url
    assert poll.run(git_poll_settings.settings) == 0
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)
    http_request_checker.assert_request_was_made({"cl": [change]})


def test_success_two_changes(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # make changes in workspace
    change1 = git_poll_settings.server.make_a_change()
    change2 = git_poll_settings.server.make_a_change()

    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    http_request_checker.assert_request_was_made({"cl": [change1]})
    http_request_checker.assert_request_was_made({"cl": [change2]})


def test_changes_several_times(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # make changes in workspace
    change1 = git_poll_settings.server.make_a_change()
    change2 = git_poll_settings.server.make_a_change()

    # run poll and trigger the urls
    assert poll.run(git_poll_settings.settings) == 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    http_request_checker.assert_request_was_made({"cl": [change1]})
    http_request_checker.assert_request_was_made({"cl": [change2]})

    # make more changes in workspace
    stdout_checker.reset()
    http_request_checker.reset()
    change3 = git_poll_settings.server.make_a_change()
    change4 = git_poll_settings.server.make_a_change()

    # run poll and trigger urls for the new changes only
    assert poll.run(git_poll_settings.settings) == 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change3)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change4)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change2)

    http_request_checker.assert_request_was_made({"cl": [change3]})
    http_request_checker.assert_request_was_made({"cl": [change4]})
    http_request_checker.assert_request_was_not_made({"cl": [change1]})
    http_request_checker.assert_request_was_not_made({"cl": [change2]})


def test_max_number_commits(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make changes in polled branch
    allowed_commits_number = git_poll_settings.settings.Poller.max_number
    changes_to_polled = [git_poll_settings.server.commit_new_file() for _ in range(allowed_commits_number + 1)]

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits(changes_to_polled[1:],
                          stdout_checker,
                          http_request_checker)
    # Ensure that oldest commit is beyond "allowed_commits_number" and is not polled
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_polled[0])


def test_merge_one_branch_ff(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_settings.server.commit_new_file()
    # make a branch from polled and add 2 new commits
    changes_to_branch = make_branch_with_changes(git_poll_settings.server, "test_branch", 2)
    # merge created branch to the polled using fast-forward option
    git_poll_settings.server.merge_branch("test_branch", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled] + changes_to_branch,
                          stdout_checker,
                          http_request_checker)


def test_merge_one_branch_noff(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_settings.server.make_a_change()
    # make a branch from polled and add 2 new commits
    changes_to_branch = make_branch_with_changes(git_poll_settings.server, "test_branch", 2)
    # merge created branch to the polled using fast-forward option
    git_poll_settings.server.merge_branch("test_branch", fast_forward=False)
    merge_commit_id = git_poll_settings.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled] + [merge_commit_id],
                          stdout_checker,
                          http_request_checker)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch[0])
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch[1])


def test_merge_two_subsequent_branches_noff(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_settings.server.make_a_change()
    # make a branch from polled and add 1 new commit
    changes_to_first_branch = make_branch_with_changes(git_poll_settings.server, "test_branch1", 1)
    # make a branch from test_branch1 and add 1 new commit
    changes_to_second_branch = make_branch_with_changes(git_poll_settings.server, "test_branch2", 1)
    # merge created branch to the polled using fast-forward option
    git_poll_settings.server.merge_branch("test_branch2", fast_forward=False)
    merge_commit_id = git_poll_settings.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled] + [merge_commit_id],
                          stdout_checker,
                          http_request_checker)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_first_branch[0])
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_second_branch[0])


def test_merge_two_subsequent_branches_ff(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_settings.server.commit_new_file()
    # make a branch from polled and add 1 new commit
    changes_to_first_branch = make_branch_with_changes(git_poll_settings.server, "test_branch1", 1)
    # make a branch from test_branch and add 1 new commit
    changes_to_second_branch = make_branch_with_changes(git_poll_settings.server, "test_branch2", 1,
                                                        branch_from="test_branch1")
    # merge created branch to the polled using fast-forward option
    git_poll_settings.server.merge_branch("test_branch2", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled] + changes_to_first_branch + changes_to_second_branch,
                          stdout_checker,
                          http_request_checker)


def test_merge_one_branch_noff_1_commit_behind(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make a branch from polled
    git_poll_settings.server.make_branch("test_branch")
    # make change to the polled branch
    git_poll_settings.server.switch_branch(git_poll_settings.server.target_branch)
    change_to_polled = git_poll_settings.server.commit_new_file()
    # make change to created test branch
    git_poll_settings.server.switch_branch("test_branch")
    changes_to_branch = git_poll_settings.server.commit_new_file()
    # merge test branch to the polled
    git_poll_settings.server.switch_branch(git_poll_settings.server.target_branch)
    git_poll_settings.server.merge_branch("test_branch", fast_forward=False)
    merge_commit_id = git_poll_settings.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled, merge_commit_id],
                          stdout_checker,
                          http_request_checker)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch)


@pytest.mark.xfail
def test_merge_ff_commit_merged_from_polled(stdout_checker, http_request_checker, git_poll_settings):
    # initialize working directory with initial data
    assert poll.run(git_poll_settings.settings) == 0

    # ACT
    # make a branch from polled
    git_poll_settings.server.make_branch("test_branch")
    # make a change to the polled branch
    git_poll_settings.server.switch_branch(git_poll_settings.server.target_branch)
    change_to_polled = git_poll_settings.server.make_a_change()
    # make a change to created test branch
    git_poll_settings.server.switch_branch("test_branch")
    change_to_branch = git_poll_settings.server.commit_new_file()
    # merge polled branch to the current
    # fast-forward is not possible in this case
    git_poll_settings.server.merge_branch(git_poll_settings.server.target_branch, fast_forward=False)
    merge_commit_to_branch = git_poll_settings.server.get_last_commit()
    # merge test branch to the polled using fast forward
    git_poll_settings.server.switch_branch(git_poll_settings.server.target_branch)
    git_poll_settings.server.merge_branch("test_branch", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    assert poll.run(git_poll_settings.settings) == 0
    assert_polled_commits([change_to_polled, change_to_branch],
                          stdout_checker,
                          http_request_checker)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + merge_commit_to_branch)
