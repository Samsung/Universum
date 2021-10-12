# pylint: disable = redefined-outer-name

import pytest

from universum import __main__
from . import git_utils, perforce_utils, utils


def test_p4_success_command_line_no_changes(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = __main__.main(["poll", "-ot", "term",
                            "-vt", "p4",
                            "-f", str(db_file),
                            "-p4p", perforce_workspace.p4.port,
                            "-p4u", perforce_workspace.p4.user,
                            "-p4P", perforce_workspace.p4.password,
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
                            "-p4P", perforce_workspace.p4.password,
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


class PollerParameters:
    def __init__(self, log_exception_checker, stdout_checker, http_check, environment):
        self.log_exception_checker = log_exception_checker
        self.stdout_checker = stdout_checker
        self.http_check = http_check
        self.poll_settings = environment.settings
        self.environment = environment

    def make_a_change(self):
        return self.environment.vcs_client.make_a_change()


@pytest.fixture()
def poll_parameters(log_exception_checker, stdout_checker, http_check):
    def inner(environment):
        return PollerParameters(log_exception_checker, stdout_checker, http_check, environment)

    yield inner


@pytest.fixture(params=["git", "p4"])
def poll_environment(request, perforce_workspace, git_client, tmpdir):
    if request.param == "git":
        yield git_utils.GitTestEnvironment(git_client, tmpdir, test_type="poll")
    else:
        yield perforce_utils.P4TestEnvironment(perforce_workspace, tmpdir, test_type="poll")


def test_error_one_change(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    # make change in workspace
    change = parameters.make_a_change()

    # run poll again and fail triggering url because there is no server
    assert __main__.run(parameters.poll_settings) != 0

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)

    # there is no listening server
    parameters.log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_success_one_change(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    # make change in workspace
    change = parameters.make_a_change()

    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)
    parameters.http_check.assert_request_was_made({"cl": [change]})
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)


def test_success_two_changes(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    # make changes in workspace
    change1 = parameters.make_a_change()
    change2 = parameters.make_a_change()

    # run poll again and trigger the url twice
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change1]})
    parameters.http_check.assert_request_was_made({"cl": [change2]})


def test_changes_several_times(poll_parameters, poll_environment):
    parameters = poll_parameters(poll_environment)

    # initialize working directory with initial data
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    # make changes in workspace
    change1 = parameters.make_a_change()
    change2 = parameters.make_a_change()

    # run poll and trigger the urls
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change1]})
    parameters.http_check.assert_request_was_made({"cl": [change2]})

    # make more changes in workspace
    parameters.stdout_checker.reset()
    change3 = parameters.make_a_change()
    change4 = parameters.make_a_change()

    # run poll and trigger urls for the new changes only
    parameters.http_check.assert_success_and_collect(__main__.run, parameters.poll_settings)

    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change3)
    parameters.stdout_checker.assert_has_calls_with_param("==> Detected commit " + change4)
    parameters.stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change1)
    parameters.stdout_checker.assert_absent_calls_with_param("==> Detected commit " + change2)

    parameters.http_check.assert_request_was_made({"cl": [change3]})
    parameters.http_check.assert_request_was_made({"cl": [change4]})
    parameters.http_check.assert_request_was_not_made({"cl": [change1]})
    parameters.http_check.assert_request_was_not_made({"cl": [change2]})


def test_poll_local_vcs(tmpdir):
    settings = utils.create_empty_settings("poll")
    settings.Vcs.type = "none"
    settings.Poll.db_file = tmpdir / "poll.json"
    settings.JenkinsServerForTrigger.trigger_url = "https://localhost/?cl=%s"
    settings.AutomationServer.type = "jenkins"
    settings.ProjectDirectory.project_root = str(tmpdir.mkdir("project_root"))

    assert __main__.run(settings) == 0
