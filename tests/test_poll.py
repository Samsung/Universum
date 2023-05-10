# pylint: disable = redefined-outer-name

from typing import Union
import pathlib
import pytest

from universum import __main__
from .conftest import FuzzyCallChecker
from .git_utils import GitServer, GitClient, GitTestEnvironment
from .perforce_utils import PerforceWorkspace, P4TestEnvironment
from .utils import LocalTestEnvironment


def test_poll_local_vcs(tmp_path: pathlib.Path):
    env = LocalTestEnvironment(tmp_path, "poll")
    env.run()


def test_p4_success_command_line_no_changes(stdout_checker: FuzzyCallChecker,
                                            perforce_workspace: PerforceWorkspace,
                                            tmp_path: pathlib.Path):
    db_file = tmp_path / "p4poll.json"
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "p4",
                            "-f", str(db_file),
                            "-p4p", perforce_workspace.server.port,
                            "-p4u", perforce_workspace.server.user,
                            "-p4P", perforce_workspace.server.password,
                            "-p4d", perforce_workspace.depot,
                            "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_git_success_command_line_no_changes(stdout_checker: FuzzyCallChecker,
                                             git_server: GitServer,
                                             tmp_path: pathlib.Path):
    db_file = tmp_path / "gitpoll.json"
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "git",
                            "-f", str(db_file),
                            "-gr", git_server.url,
                            "-grs", git_server.target_branch,
                            "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_p4_error_command_line_wrong_port(stdout_checker: FuzzyCallChecker,
                                          perforce_workspace: PerforceWorkspace,
                                          tmp_path: pathlib.Path):
    db_file = tmp_path / "p4poll.json"
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "p4",
                            "-f", str(db_file),
                            "-p4p", "127.0.0.1:1024",
                            "-p4u", perforce_workspace.server.user,
                            "-p4P", perforce_workspace.server.password,
                            "-p4d", perforce_workspace.depot,
                            "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("TCP connect to 127.0.0.1:1024 failed.")


def test_git_error_command_line_wrong_port(stdout_checker: FuzzyCallChecker,
                                           git_server: GitServer,
                                           tmp_path: pathlib.Path):
    db_file = tmp_path / "gitpoll.json"
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "git",
                            "-f", str(db_file),
                            "-gr", "file:///non-existing-directory",
                            "-grs", git_server.target_branch,
                            "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("Cmd('git') failed due to: exit code(128)")


@pytest.fixture(params=["git", "p4"])
def poll_environment(request, perforce_workspace: PerforceWorkspace, git_client: GitClient, tmp_path: pathlib.Path):
    if request.param == "git":
        yield GitTestEnvironment(git_client, tmp_path, test_type="poll")
    else:
        yield P4TestEnvironment(perforce_workspace, tmp_path, test_type="poll")


def test_error_one_change(stdout_checker: FuzzyCallChecker, log_exception_checker: FuzzyCallChecker,
                          poll_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make change in workspace
    change = poll_environment.vcs_client.make_a_change()

    # run poll again and fail triggering url because there is no server
    poll_environment.run(expect_failure=True)

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)

    # there is no listening server
    log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_success_one_change(stdout_checker: FuzzyCallChecker, poll_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make change in workspace
    change = poll_environment.vcs_client.make_a_change()

    collected_http = poll_environment.run_with_http_server()
    collected_http.assert_request_was_made({"cl": [change]})
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)


def test_success_two_changes(stdout_checker: FuzzyCallChecker, poll_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make changes in workspace
    change1 = poll_environment.vcs_client.make_a_change()
    change2 = poll_environment.vcs_client.make_a_change()

    # run poll again and trigger the url twice
    collected_http = poll_environment.run_with_http_server()

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    collected_http.assert_request_was_made({"cl": [change1]})
    collected_http.assert_request_was_made({"cl": [change2]})


def test_changes_several_times(stdout_checker: FuzzyCallChecker, poll_environment: Union[GitTestEnvironment, P4TestEnvironment]):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make changes in workspace
    change1 = poll_environment.vcs_client.make_a_change()
    change2 = poll_environment.vcs_client.make_a_change()

    # run poll and trigger the urls
    collected_http = poll_environment.run_with_http_server()

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    collected_http.assert_request_was_made({"cl": [change1]})
    collected_http.assert_request_was_made({"cl": [change2]})

    # make more changes in workspace
    stdout_checker.reset()
    change3 = poll_environment.vcs_client.make_a_change()
    change4 = poll_environment.vcs_client.make_a_change()

    # run poll and trigger urls for the new changes only
    collected_http = poll_environment.run_with_http_server()

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change3)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change4)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change1)
    stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change2)

    collected_http.assert_request_was_made({"cl": [change3]})
    collected_http.assert_request_was_made({"cl": [change4]})
    collected_http.assert_request_was_not_made({"cl": [change1]})
    collected_http.assert_request_was_not_made({"cl": [change2]})
