# pylint: disable = redefined-outer-name, abstract-method

import pytest

from universum import __main__
from universum.modules.vcs.github_vcs import GithubToken
from . import utils


class ReportEnvironment(utils.TestEnvironment):
    def __init__(self, directory, client):
        super(ReportEnvironment, self).__init__(directory, "main")

        self.settings.Vcs.type = "github"
        self.settings.MainVcs.report_to_review = True
        self.settings.GitVcs.repo = client.server.url
        commit_id = str(client.repo.remotes.origin.refs[client.server.target_branch].commit)
        self.settings.GitMainVcs.checkout_id = commit_id
        self.settings.GithubToken.integration_id = "1234"
        self.settings.GithubToken.key = "this is key"
        self.settings.GithubTokenWithInstallation.installation_id = "5678"
        self.settings.GithubMainVcs.check_id = "123"
        self.settings.GithubMainVcs.api_url = "http://localhost/"
        self.settings.Reporter.report_start = True
        self.settings.Reporter.report_success = True

        repo_name = str(client.root_directory).rsplit("client", 1)[0]
        self.path = "http://localhost/repos" + repo_name + "server/check-runs/123"


@pytest.fixture()
def report_environment(tmpdir, git_client):
    yield ReportEnvironment(tmpdir, git_client)


def test_github_run(http_check, report_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")

    http_check.assert_success_and_collect(__main__.run, report_environment.settings,
                                          url=report_environment.path, method="PATCH")
    http_check.assert_request_body_contained("status", "in_progress")
    http_check.assert_request_body_contained("status", "completed")
    http_check.assert_request_body_contained("conclusion", "success")
