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
        self.settings.GithubHandler.trigger_url = "http://localhost"

        self.settings.GithubToken.integration_id = "INTEGRATION_ID"
        self.settings.GithubToken.key = "this is key"

        self.check_suite_payload = """
{
  "action": "requested",
  "repository": {
    "url": "http://localhost"
  },
  "check_suite": {
    "head_sha": "check_suite_head_sha"
  },
  "installation": {
    "id": "installation_id"
  }
}"""
        self.check_suite_url = "http://localhost/check-runs"
        self.check_run_payload = """
{
  "action": "requested",
  "check_run": {
    "app": {
      "id": "INTEGRATION_ID"
    },
    "check_suite": {
        "head_branch": "check_run_check_suite_head_branch"
    },
    "head_sha": "check_run_head_sha",
    "id": "check_run_id"
  },
  "repository": {
    "clone_url": "repository_clone_url"
  },
  "installation": {
  "id": "installation_id"
  }
}"""
        self.check_run_url = "http://localhost/"


@pytest.fixture()
def github_handler_environment(tmpdir):
    yield GithubHandlerEnvironment(tmpdir)


@pytest.fixture(autouse=True)
def mock_token(monkeypatch):
    monkeypatch.setattr(GithubToken, 'get_token', lambda *args, **kwargs: "this is token")


def test_success_github_handler_check_suite(http_check, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_suite"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_suite_payload
    http_check.assert_success_and_collect(__main__.run, github_handler_environment.settings,
                                          url=github_handler_environment.check_suite_url, method="POST")
    http_check.assert_request_headers_contained('Accept', 'application/vnd.github.antiope-preview+json')
    http_check.assert_request_headers_contained('Authorization', "token this is token")


def test_success_github_handler_check_run(http_check, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    http_check.assert_success_and_collect(__main__.run, github_handler_environment.settings,
                                          url=github_handler_environment.check_run_url, method="GET")


def test_error_github_handler_not_a_json(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "not a JSON"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_wrong_json_syntax(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "{'key': 'value'}"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_multiple_payloads(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "[{},{}]"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Parsed payload JSON does not correspond to expected format")


def test_error_github_handler_empty_json(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "{}"
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Could not find key 'action' in provided payload")


def test_error_github_handler_json_missing_key(stdout_checker, github_handler_environment):
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


def test_error_github_handler_no_github_server(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_suite"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_suite_payload
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Failed to establish a new connection: [Errno 111] Connection refused")


def test_error_github_handler_no_jenkins_server(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    assert __main__.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Failed to establish a new connection: [Errno 111] Connection refused")
