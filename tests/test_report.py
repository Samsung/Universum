#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import httpretty
import pytest

import universum
import utils


class ReportEnvironment(utils.TestEnvironment):
    def __init__(self, directory, client):
        super(ReportEnvironment, self).__init__(directory, "main")

        self.settings.Vcs.type = "github"
        self.settings.MainVcs.report_to_review = True
        self.settings.GitVcs.repo = client.server.url
        commit_id = unicode(client.repo.remotes.origin.refs[client.server.target_branch].commit)
        self.settings.GitMainVcs.checkout_id = commit_id
        self.settings.GithubMainVcs.token = "token"
        self.settings.GithubMainVcs.api_url = "http://api.github.com/"
        self.settings.Reporter.report_start = True
        self.settings.Reporter.report_success = True

        self.path = "http://api.github.com/repos" + \
                    unicode(client.root_directory).strip("client") + \
                    "server/check-runs"


@pytest.fixture()
def report_environment(tmpdir, git_client):
    yield ReportEnvironment(tmpdir, git_client)


# def test_github_run(stdout_checker, http_check, report_environment):
def test_github_run(http_check, report_environment):
    http_check.assert_success_and_collect(universum.run, report_environment.settings,
                                          url=report_environment.path, method="POST")
    requests = httpretty.httpretty.latest_requests
    print requests
    # http_check.assert_request_was_made({"status": "completed"})
    # stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)
