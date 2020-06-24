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

        self.settings.GithubHandler.payload = ""
        self.settings.GithubHandler.event = "check_suite"
        self.settings.GithubHandler.trigger_url = "http://example.com/non-existent"

        self.settings.GithubToken.integration_id = "1234"
        self.settings.GithubToken.key = "this is key"


@pytest.fixture()
def github_handler_environment(tmpdir):
    yield GithubHandlerEnvironment(tmpdir)


def test_success_github_handler(http_check, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    url = "http://example.com/check-runs"
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
    http_check.assert_success_and_collect(__main__.run, github_handler_environment.settings, url=url, method="POST")


def test_error_github_handler_not_a_json(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = "not a JSON"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_wrong_json_syntax(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = "{'key': 'value'}"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_multiple_payloads(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = "[{},{}]"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Parsed payload JSON does not correspond to expected format")


def test_error_github_handler_empty_json(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = "{}"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Could not find key 'action' in provided payload")


def test_error_github_handler_json_missing_key(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")
    github_handler_environment.settings.GithubHandler.payload = """
    {
      "action": "requested",
      "repository": {
        "url": "http://example.com"
      },
      "check_suite": {
        "head_sha": "1234"
      }
    }
    """
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Could not find key 'installation' in provided payload")


def test_error_github_handler_no_github_server(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")

    github_handler_environment.settings.GithubHandler.event = "check_suite"
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
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("404 Client Error: Not Found for url: http://example.com/check-runs")


def test_error_github_handler_no_jenkins_server(stdout_checker, github_handler_environment, monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")

    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = """
{
  "action": "requested",
  "check_run": {
    "app": {
      "id": "1234"
    },
    "check_suite": {
        "head_branch": "master"
    },
    "head_sha": "5678",
    "id": "0"
  },
  "repository": {
    "clone_url": "http://example.com"
  },
  "installation": {
  "id": "123456"
  }
}
"""
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("404 Client Error: Not Found for url: http://example.com/non-existent?")
