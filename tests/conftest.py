# -*- coding: UTF-8 -*-
# pylint: disable = redefined-outer-name

import httpretty
import pytest
import mock

pytest_plugins = ['tests.perforce_utils', 'tests.git_utils', 'tests.deployment_utils']


class FuzzyCallChecker(object):
    def __init__(self, mock_object):
        self.mock_object = mock_object

    def _assertion_message(self, string_to_find):
        return '\nExpected param: %s\nActual list: %r' % (string_to_find, self.mock_object.mock_calls)

    def _find_call_with_param(self, string_param):
        for call in self.mock_object.mock_calls:
            _, args, _ = call
            for arg in args:
                if string_param in arg:
                    return True
        # return explicit False
        return False

    def reset(self):
        self.mock_object.reset_mock()

    def assert_has_calls_with_param(self, string_param):
        assert self._find_call_with_param(string_param), 'String parameter is not found in call list. %s' \
                                                         % (self._assertion_message(string_param))

    def assert_absent_calls_with_param(self, string_param):
        assert not self._find_call_with_param(string_param), 'String parameter is found in call list, ' \
                                                             'but is not expected to be found.%s' \
                                                             % (self._assertion_message(string_param))


@pytest.fixture()
def stdout_checker(request):
    with mock.patch('_universum.modules.output.terminal_based_output.stdout') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


@pytest.fixture()
def log_exception_checker(request):
    with mock.patch('_universum.modules.output.terminal_based_output.TerminalBasedOutput.log_exception') as logging_mock:
        result = FuzzyCallChecker(logging_mock)
        yield result


class HttpChecker(object):
    @staticmethod
    def assert_request_was_made(query):
        queries = []
        for request in httpretty.httpretty.latest_requests:
            if request.querystring == query:
                return
            queries.append(request.querystring)

        assert False, 'Query string is not found in calls to http server.\n' \
                      'Expected: %s\nActual: %r' % (query, queries)

    @staticmethod
    def assert_request_was_not_made(query):
        queries = []
        for request in httpretty.httpretty.latest_requests:
            if request.querystring == query:
                assert False, 'Query string was found in calls to http server.' \
                              '\nExpected: %s\nActual: %r' % (query, queries)
            queries.append(request.querystring)

    @staticmethod
    def assert_request_body_contained(key, value):
        results = []
        for request in httpretty.httpretty.latest_requests:
            if key in request.parsed_body:
                if request.parsed_body[key] == value:
                    return
                results.append(request.parsed_body[key])

        if not results:
            text = "No requests with field '{}' found in calls to http server".format(key)
        else:
            text = "No requests with field '{}' set to '{}' found in calls to http server.\n" \
                   "However, requests with following values were made: {}".format(key, value, results)
        assert False, text

    @staticmethod
    def assert_success_and_collect(function, params, url="https://localhost/", method="GET"):
        httpretty.reset()
        httpretty.enable()
        if method == "GET":
            hmethod = httpretty.GET
        elif method == "POST":
            hmethod = httpretty.POST
        else:
            hmethod = httpretty.PATCH
        httpretty.register_uri(hmethod, url)

        try:
            assert function(params) == 0
        finally:
            httpretty.disable()


@pytest.fixture()
def http_check(request):
    yield HttpChecker()


def check_output((out, err)):
    assert not err, "Stderr detected!"
    for text in ["Traceback", "Exception"]:
        assert text not in out, text + " detected in stdout!"


# pylint: disable = protected-access
@pytest.fixture(autouse=True)
def detect_fails(capsys):
    yield capsys
    check_output(capsys.readouterr())
    check_output(capsys._outerr)
