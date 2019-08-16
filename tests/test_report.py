#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import pytest

import universum, utils


class ReportEnvironment(utils.TestEnvironment):
    def __init__(self, directory, local_sources):
        super(ReportEnvironment, self).__init__(directory, "main")

        self.settings.Vcs.type = "none"
        self.settings.MainVcs.report_to_review = True
        self.settings.LocalMainVcs.source_dir = unicode(local_sources.root_directory)


@pytest.fixture()
def report_environment(tmpdir, local_sources):
    yield ReportEnvironment(tmpdir, local_sources)


def test_github_run(stdout_checker, http_check, report_environment):

    http_check.assert_success_and_collect(universum.run, report_environment.settings)

    # http_check.assert_request_was_made({"cl": [change]})
    # stdout_checker.assert_has_calls_with_param("==> Detected commit " + change)
