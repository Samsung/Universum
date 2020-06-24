# pylint: disable = redefined-outer-name, abstract-method

import pytest

from universum import __main__
from universum.modules.vcs.github_vcs import GithubToken
from .utils import create_empty_settings


class GithubHandlerEnvironment:
    def __init__(self, directory):
        self.temp_dir = directory
        self.settings = create_empty_settings("github-handler")
        self.settings.Output.type = "term"

        self.settings.GithubHandler.event = "check_suite"
        self.settings.GithubHandler.trigger_url = "http://example.com"
        self.path = "http://example.com/check-runs"

        self.settings.GithubToken.integration_id = "1234"
        self.settings.GithubToken.key = "this is key"


@pytest.fixture()
def github_handler_environment(tmpdir):
    yield GithubHandlerEnvironment(tmpdir)


def test_success_github_handler(http_check, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = """
{
  "action": "requested",
  "repository": {
    "url": "http://example.com"
  },
  "check_suite": {
    "head_sha": "1234"
  },
  "installation": {
    "id": "1234"
  }
}
"""

    http_check.assert_success_and_collect(__main__.run, github_handler_environment.settings,
                                          url=github_handler_environment.path, method="POST")
