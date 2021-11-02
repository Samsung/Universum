# pylint: disable = redefined-outer-name

import pytest

from universum import __main__
from . import git_utils, perforce_utils, utils


def test_poll_local_vcs(tmpdir):
    env = utils.LocalTestEnvironment(tmpdir, "poll")
    env.run()


def test_p4_success_command_line_no_changes(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "p4",
                            "-f", str(db_file),
                            "-p4p", perforce_workspace.p4.port,
                            "-p4u", perforce_workspace.p4.user,
                            "-p4P", perforce_workspace.non_token_password,
                            "-p4d", "//depot/...",
                            "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_git_success_command_line_no_changes(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "git",
                            "-f", str(db_file),
                            "-gr", git_server.url,
                            "-grs", git_server.target_branch,
                            "-jtu", "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_p4_error_command_line_wrong_port(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "p4",
                            "-f", str(db_file),
                            "-p4p", "127.0.0.1:1024",
                            "-p4u", perforce_workspace.p4.user,
                            "-p4P", perforce_workspace.non_token_password,
                            "-p4d", "//depot/...",
                            "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("TCP connect to 127.0.0.1:1024 failed.")


def test_git_error_command_line_wrong_port(stdout_checker, git_server, tmpdir):
    db_file = tmpdir.join("gitpoll.json")
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "git",
                            "-f", str(db_file),
                            "-gr", "file:///non-existing-directory",
                            "-grs", git_server.target_branch,
                            "-jtu", "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("Cmd('git') failed due to: exit code(128)")


@pytest.fixture(params=["git", "p4"])
def poll_environment(request, perforce_workspace, git_client, tmpdir):
    if request.param == "git":
        yield git_utils.GitTestEnvironment(git_client, tmpdir, test_type="poll")
    else:
        yield perforce_utils.P4TestEnvironment(perforce_workspace, tmpdir, test_type="poll")


def test_error_one_change(stdout_checker, log_exception_checker, poll_environment):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make change in workspace
    change = poll_environment.vcs_client.make_a_change()

    # run poll again and fail triggering url because there is no server
    poll_environment.run(expect_failure=True)

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)

    # there is no listening server
    log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_success_one_change(stdout_checker, poll_environment):
    # initialize working directory with initial data
    poll_environment.run_with_http_server()

    # make change in workspace
    change = poll_environment.vcs_client.make_a_change()

    collected_http = poll_environment.run_with_http_server()
    collected_http.assert_request_was_made({"cl": [change]})
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)


def test_success_two_changes(stdout_checker, poll_environment):
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


def test_changes_several_times(stdout_checker, poll_environment):
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
