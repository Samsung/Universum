# pylint: disable = redefined-outer-name

import re
from unittest import mock

import httpretty
import pytest

pytest_plugins = ['tests.perforce_utils', 'tests.git_utils', 'tests.deployment_utils']


class FuzzyCallChecker:
    def __init__(self, mock_object):
        self.mock_object = mock_object

    def _assertion_message(self, string_to_find):
        return '\nExpected param: %s\nActual list: %r' % (string_to_find, self.mock_object.mock_calls)

    def _find_call_with_param(self, pattern_to_search, is_regexp):
        if is_regexp:
            regexp = re.compile(pattern_to_search)

        for call in self.mock_object.mock_calls:
            _, args, _ = call
            for arg in args:
                if is_regexp:
                    if regexp.search(arg) is not None:
                        return True
                else:
                    if pattern_to_search in arg:
                        return True
        # return explicit False
        return False

    def reset(self):
        self.mock_object.reset_mock()

    def assert_has_calls_with_param(self, pattern_to_search, is_regexp=False):
        assert self._find_call_with_param(pattern_to_search, is_regexp), \
            'Pattern is not found in call list. ' + \
            self._assertion_message(pattern_to_search)

    def assert_absent_calls_with_param(self, pattern_to_search, is_regexp=False):
        assert not self._find_call_with_param(pattern_to_search, is_regexp), \
            'Pattern is found in call list, but is not expected to be found. ' + \
            self._assertion_message(pattern_to_search)


@pytest.fixture()
def stdout_checker(request):
    with mock.patch('universum.modules.output.terminal_based_output.stdout') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


@pytest.fixture()
def log_exception_checker(request):
    with mock.patch('universum.modules.output.terminal_based_output.TerminalBasedOutput.log_exception') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


class HttpChecker:

    @staticmethod
    def assert_request_with_query(query, ensure):
        queries = []
        for request in httpretty.httpretty.latest_requests:
            if request.querystring == query:
                if ensure:
                    return
                assert False, 'Query string was found in calls to http server.\n' \
                              'Expected: %s\nActual: %r' % (query, queries)
            queries.append(request.querystring)

        if ensure:
            assert False, 'Query string is not found in calls to http server.\n' \
                          'Expected: %s\nActual: %r' % (query, queries)

    @staticmethod
    def assert_request_was_made(query):
        HttpChecker.assert_request_with_query(query, ensure=True)

    @staticmethod
    def assert_request_was_not_made(query):
        HttpChecker.assert_request_with_query(query, ensure=False)

    @staticmethod
    def assert_request_contained(key, value, target):
        results = []
        for request in httpretty.httpretty.latest_requests:
            if target == "query param":
                check_target = request.querystring
            elif target == "header":
                check_target = request.headers
            elif target == "body field":
                check_target = request.parsed_body
            else:
                assert False, f"This type of check ('{target}') is not implemented"

            if key in check_target:
                if (target == "query param") and (value in check_target[key]):
                    return
                if check_target[key] == value:
                    return
                results.append(check_target[key])

        if not results:
            text = f"No requests with {target} '{key}' found in calls to http server"
        else:
            text = f"No requests with {target} '{key}' set to '{value}' found in calls to http server.\n"
            text += f"However, requests with following values were made: {results}"
        assert False, text

    @staticmethod
    def assert_request_query_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "query param")

    @staticmethod
    def assert_request_headers_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "header")

    @staticmethod
    def assert_request_body_contained(key, value):
        HttpChecker.assert_request_contained(key, value, "body field")

    @staticmethod
    def assert_and_collect(function, params, url, method, result, status):
        httpretty.reset()
        httpretty.enable()
        if method == "GET":
            hmethod = httpretty.GET
        elif method == "POST":
            hmethod = httpretty.POST
        else:
            hmethod = httpretty.PATCH
        httpretty.register_uri(hmethod, url, status=status)

        try:
            assert function(params) == result
        finally:
            httpretty.disable()

    @staticmethod
    def assert_success_and_collect(function, params, url="https://localhost/", method="GET"):
        HttpChecker.assert_and_collect(function, params, url, method, result=0, status='200')

    @staticmethod
    def assert_404_and_collect(function, params, url="https://localhost/", method="GET"):
        HttpChecker.assert_and_collect(function, params, url, method, result=1, status='404')


@pytest.fixture()
def http_check(request):
    yield HttpChecker()


@pytest.fixture(autouse=True)
def detect_fails(capsys, request):
    yield capsys

    out, err = capsys.readouterr()
    assert not err, f"Error detected: {err}"
    for text in ["Traceback", "Exception"]:
        assert text not in out, f"'{text}' detected in stdout!"

    if request.node.name == 'test_teardown_fixture_output_verification':
        assert out == "TearDown fixture output must be handled by 'detect_fails' fixture\n"
