#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import pytest

import poll
from _universum import gravity
from . import default_args


def test_success_command_line_poll_no_changes(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = poll.main(["-ot", "term",
                        "-vt", "p4",
                        "-f", unicode(db_file),
                        "-p4p", perforce_workspace.p4.port,
                        "-p4u", perforce_workspace.p4.user,
                        "-p4P", perforce_workspace.p4.password,
                        "-p4d", "//depot/...", "-u",
                        "https://localhost/?%s"])
    assert result == 0
    stdout_checker.assert_has_calls_with_param("==> No changes detected")


def test_error_command_line_wrong_port(stdout_checker, perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")
    result = poll.main(["-ot", "term",
                        "-vt", "p4",
                        "-f", unicode(db_file),
                        "-p4p", "127.0.0.1:1024",
                        "-p4u", perforce_workspace.p4.user,
                        "-p4P", perforce_workspace.p4.password,
                        "-p4d", "//depot/...", "-u",
                        "https://localhost/?%s"])
    assert result != 0
    stdout_checker.assert_has_calls_with_param("TCP connect to 127.0.0.1:1024 failed.")


@pytest.fixture()
def p4_poll_settings(perforce_workspace, tmpdir):
    db_file = tmpdir.join("p4poll.json")

    argument_parser = default_args.ArgParserWithDefault()
    gravity.define_arguments_recursive(poll.Poller, argument_parser)

    settings = argument_parser.parse_args([])
    settings.workspace = perforce_workspace

    settings.Poller.db_file = unicode(db_file)
    settings.Output.type = "term"
    settings.FileManager.vcs = "p4"
    settings.BasicServer.url = "https://localhost/?cl=%s"

    settings.PerforceVcs.project_depot_path = perforce_workspace.depot
    settings.PerforceVcs.port = perforce_workspace.p4.port
    settings.PerforceVcs.user = perforce_workspace.p4.user
    settings.PerforceVcs.password = perforce_workspace.p4.password

    yield settings


def make_one_change(p4_poll_settings):
    tmpfile = p4_poll_settings.workspace.tmpfile
    p4_poll_settings.workspace.p4.run("edit", str(tmpfile))
    tmpfile.write("Change #1 " + str(tmpfile))

    change = p4_poll_settings.workspace.p4.run_change("-o")[0]
    change["Description"] = "Test submit #1"

    committed_change = p4_poll_settings.workspace.p4.run_submit(change)

    cl = next((x["submittedChange"] for x in committed_change if "submittedChange" in x))

    return cl


def test_error_one_change(log_exception_checker, stdout_checker, p4_poll_settings):
    # initialize working directory with initial data
    assert poll.run(p4_poll_settings) == 0

    # make change in workspace
    cl = make_one_change(p4_poll_settings)

    # run poll again and fail triggering url because there is no server
    assert poll.run(p4_poll_settings) != 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + cl)

    # there is no listening server
    log_exception_checker.assert_has_calls_with_param("[Errno 111] Connection refused")


def test_success_one_change(stdout_checker, http_request_checker, p4_poll_settings):
    # initialize working directory with initial data
    assert poll.run(p4_poll_settings) == 0

    # make change in workspace
    cl = make_one_change(p4_poll_settings)

    # run poll again and trigger the url
    assert poll.run(p4_poll_settings) == 0
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + cl)
    http_request_checker.assert_request_was_made({"cl": [cl]})


def test_success_two_changes(stdout_checker, http_request_checker, p4_poll_settings):
    # initialize working directory with initial data
    assert poll.run(p4_poll_settings) == 0

    # make changes in workspace
    cl1 = make_one_change(p4_poll_settings)
    cl2 = make_one_change(p4_poll_settings)

    # run poll again and trigger the url twice
    assert poll.run(p4_poll_settings) == 0

    stdout_checker.assert_has_calls_with_param("==> Detected commit " + cl1)
    stdout_checker.assert_has_calls_with_param("==> Detected commit " + cl2)

    http_request_checker.assert_request_was_made({"cl": [cl1]})
    http_request_checker.assert_request_was_made({"cl": [cl2]})
