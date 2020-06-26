# pylint: disable = redefined-outer-name, abstract-method

import pytest

from universum import __main__ as universum
from universum.modules.vcs.github_vcs import GithubToken
from .utils import create_empty_settings


class GithubHandlerEnvironment:
    def __init__(self, directory):
        self.temp_dir = directory
        self.settings = create_empty_settings("github-handler")
        self.settings.Output.type = "term"

        self.settings.GithubHandler.payload = "{}"
        self.settings.GithubHandler.event = "check_run"
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
    def mocking_function(token_handler, parsed_id):
        assert parsed_id == 'installation_id'
        return "TOKEN_STRING"

    monkeypatch.setattr(GithubToken, 'get_token', mocking_function)


def test_success_github_handler_check_suite(http_check, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_suite"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_suite_payload
    http_check.assert_success_and_collect(universum.run, github_handler_environment.settings,
                                          url=github_handler_environment.check_suite_url, method="POST")
    http_check.assert_request_headers_contained('Authorization', "token TOKEN_STRING")
    http_check.assert_request_body_contained("head_sha", "check_suite_head_sha")


def test_success_github_handler_check_run(http_check, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    http_check.assert_success_and_collect(universum.run, github_handler_environment.settings,
                                          url=github_handler_environment.check_run_url, method="GET")
    http_check.assert_request_query_contained("GIT_REFSPEC", "check_run_check_suite_head_branch")
    http_check.assert_request_query_contained("GIT_CHECKOUT_ID", "check_run_head_sha")
    http_check.assert_request_query_contained("GITHUB_CHECK_ID", "check_run_id")
    http_check.assert_request_query_contained("GIT_REPO", "repository_clone_url")
    http_check.assert_request_query_contained("GITHUB_INSTALLATION_ID", "installation_id")


def test_error_github_handler_not_a_json(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "not a JSON"
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_wrong_json_syntax(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "{'key': 'value'}"
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Provided payload value could not been parsed as JSON")


def test_error_github_handler_multiple_payloads(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "[{},{}]"
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Parsed payload JSON does not correspond to expected format")


def test_error_github_handler_empty_json(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.payload = "{}"
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Could not find key 'action' in provided payload")


def test_error_github_handler_json_missing_key(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    fixed_payload = github_handler_environment.check_run_payload.replace('"id": "installation_id"', '')
    github_handler_environment.settings.GithubHandler.payload = fixed_payload
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Could not find key 'id' in provided payload")


def test_error_github_handler_wrong_event(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "unhandled_event"
    assert not universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Unhandled event, skipping...")


def test_error_github_handler_wrong_app(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    fixed_payload = github_handler_environment.check_run_payload.replace('"id": "INTEGRATION_ID"', '"id": "wrong_id"')
    github_handler_environment.settings.GithubHandler.payload = fixed_payload
    assert not universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Unhandled event, skipping...")


def test_error_github_handler_no_github_server(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_suite"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_suite_payload
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Failed to establish a new connection: [Errno 111] Connection refused")


def test_error_github_handler_no_jenkins_server(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("Failed to establish a new connection: [Errno 111] Connection refused")


def test_error_github_handler_wrong_schema(stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    github_handler_environment.settings.GithubHandler.trigger_url = "htttttp://localhost"
    assert universum.run(github_handler_environment.settings)
    stdout_checker.assert_has_calls_with_param("No connection adapters were found for 'htttttp://localhost'")


def test_error_github_handler_404(http_check, stdout_checker, github_handler_environment):
    github_handler_environment.settings.GithubHandler.event = "check_run"
    github_handler_environment.settings.GithubHandler.payload = github_handler_environment.check_run_payload
    url = github_handler_environment.check_run_url
    http_check.assert_404_and_collect(universum.run, github_handler_environment.settings, url=url, method="GET")
    stdout_checker.assert_has_calls_with_param(f"404 Client Error: Not Found for url: {url}")
