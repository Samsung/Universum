#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import pytest

import universum, utils


class ReportEnvironment(utils.TestEnvironment):
    def __init__(self, directory, client):
        super(ReportEnvironment, self).__init__(directory, "main")

        self.settings.Vcs.type = "github"
        self.settings.MainVcs.report_to_review = True
        self.settings.GitVcs.repo = client.server.url
        self.settings.GitVcs.refspec = client.server.target_branch


@pytest.fixture()
def report_environment(tmpdir, git_client):
    yield ReportEnvironment(tmpdir, git_client)


def test_github_run(stdout_checker, http_check, report_environment):

    http_check.assert_success_and_collect(universum.run, report_environment.settings)

    # http_check.assert_request_was_made({"cl": [change]})
    # stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)
