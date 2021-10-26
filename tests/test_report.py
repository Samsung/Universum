# pylint: disable = redefined-outer-name, abstract-method

import pytest
import py

from universum.modules.vcs.github_vcs import GithubToken
from . import utils
from .git_utils import GitClient


class ReportEnvironment(utils.BaseTestEnvironment):
    def __init__(self, client: GitClient, directory: py.path.local):
        super().__init__(client, directory, "main", "")

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
        self.path: str = "http://localhost/repos" + repo_name + "server/check-runs/123"


@pytest.fixture()
def report_environment(git_client, tmpdir):
    yield ReportEnvironment(git_client, tmpdir)


def test_github_run(report_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")

    collected_http = report_environment.run_with_http_server(url=report_environment.path, method="PATCH")
    collected_http.assert_request_body_contained("status", "in_progress")
    collected_http.assert_request_body_contained("status", "completed")
    collected_http.assert_request_body_contained("conclusion", "success")
