# pylint: disable = redefined-outer-name

from typing import Optional
import pathlib
import pytest

from .conftest import FuzzyCallChecker
from .git_utils import GitTestEnvironment, GitClient, GitServer
from .utils import HttpChecker


@pytest.fixture()
def git_poll_environment(git_client: GitClient, tmp_path: pathlib.Path):
    yield GitTestEnvironment(git_client, tmp_path, test_type="poll")


def make_branch_with_changes(git_server: GitServer, branch_name: str, commits_number: int,
                             branch_from: Optional[str] = None):
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


def assert_polled_commits(commits: list, stdout_checker: FuzzyCallChecker, collected_http: HttpChecker) -> None:
    for commit in commits:
        stdout_checker.assert_has_calls_with_param("==> Detected commit " + commit)
        collected_http.assert_request_was_made({"cl": [commit]})


def test_max_number_commits(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make changes in polled branch
    allowed_commits_number: int = git_poll_environment.settings.Poll.max_number
    changes_to_polled = [git_poll_environment.server.commit_new_file() for _ in range(allowed_commits_number + 1)]

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits(changes_to_polled[1:],
                          stdout_checker,
                          collected_http)
    # Ensure that oldest commit is beyond "allowed_commits_number" and is not polled
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_polled[0])


def test_merge_one_branch_ff(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_environment.server.commit_new_file()
    # make a branch from polled and add 2 new commits
    changes_to_branch = make_branch_with_changes(git_poll_environment.server, "test_branch", 2)
    # merge created branch to the polled using fast-forward option
    git_poll_environment.server.merge_branch("test_branch", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled] + changes_to_branch,
                          stdout_checker,
                          collected_http)


def test_merge_one_branch_noff(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_environment.server.make_a_change()
    # make a branch from polled and add 2 new commits
    changes_to_branch = make_branch_with_changes(git_poll_environment.server, "test_branch", 2)
    # merge created branch to the polled using fast-forward option
    git_poll_environment.server.merge_branch("test_branch", fast_forward=False)
    merge_commit_id = git_poll_environment.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled] + [merge_commit_id],
                          stdout_checker,
                          collected_http)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch[0])
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch[1])


def test_merge_two_subsequent_branches_noff(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_environment.server.make_a_change()
    # make a branch from polled and add 1 new commit
    changes_to_first_branch = make_branch_with_changes(git_poll_environment.server, "test_branch1", 1)
    # make a branch from test_branch1 and add 1 new commit
    changes_to_second_branch = make_branch_with_changes(git_poll_environment.server, "test_branch2", 1)
    # merge created branch to the polled using fast-forward option
    git_poll_environment.server.merge_branch("test_branch2", fast_forward=False)
    merge_commit_id = git_poll_environment.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled] + [merge_commit_id],
                          stdout_checker,
                          collected_http)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_first_branch[0])
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_second_branch[0])


def test_merge_two_subsequent_branches_ff(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make changes in polled branch
    change_to_polled = git_poll_environment.server.commit_new_file()
    # make a branch from polled and add 1 new commit
    changes_to_first_branch = make_branch_with_changes(git_poll_environment.server, "test_branch1", 1)
    # make a branch from test_branch and add 1 new commit
    changes_to_second_branch = make_branch_with_changes(git_poll_environment.server, "test_branch2", 1,
                                                        branch_from="test_branch1")
    # merge created branch to the polled using fast-forward option
    git_poll_environment.server.merge_branch("test_branch2", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled] + changes_to_first_branch + changes_to_second_branch,
                          stdout_checker,
                          collected_http)


def test_merge_one_branch_noff_1_commit_behind(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make a branch from polled
    git_poll_environment.server.make_branch("test_branch")
    # make change to the polled branch
    git_poll_environment.server.switch_branch(git_poll_environment.server.target_branch)
    change_to_polled = git_poll_environment.server.commit_new_file()
    # make change to created test branch
    git_poll_environment.server.switch_branch("test_branch")
    changes_to_branch = git_poll_environment.server.commit_new_file()
    # merge test branch to the polled
    git_poll_environment.server.switch_branch(git_poll_environment.server.target_branch)
    git_poll_environment.server.merge_branch("test_branch", fast_forward=False)
    merge_commit_id = git_poll_environment.server.get_last_commit()

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled, merge_commit_id],
                          stdout_checker,
                          collected_http)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + changes_to_branch)


@pytest.mark.xfail
def test_merge_ff_commit_merged_from_polled(stdout_checker: FuzzyCallChecker, git_poll_environment: GitTestEnvironment):
    # initialize working directory with initial data
    git_poll_environment.run_with_http_server()

    # ACT
    # make a branch from polled
    git_poll_environment.server.make_branch("test_branch")
    # make a change to the polled branch
    git_poll_environment.server.switch_branch(git_poll_environment.server.target_branch)
    change_to_polled = git_poll_environment.server.make_a_change()
    # make a change to created test branch
    git_poll_environment.server.switch_branch("test_branch")
    change_to_branch = git_poll_environment.server.commit_new_file()
    # merge polled branch to the current
    # fast-forward is not possible in this case
    git_poll_environment.server.merge_branch(git_poll_environment.server.target_branch, fast_forward=False)
    merge_commit_to_branch = git_poll_environment.server.get_last_commit()
    # merge test branch to the polled using fast forward
    git_poll_environment.server.switch_branch(git_poll_environment.server.target_branch)
    git_poll_environment.server.merge_branch("test_branch", fast_forward=True)

    # ASSERT
    # run poll again and trigger the url twice
    collected_http: HttpChecker = git_poll_environment.run_with_http_server()
    assert_polled_commits([change_to_polled, change_to_branch],
                          stdout_checker,
                          collected_http)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + merge_commit_to_branch)
