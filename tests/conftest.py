# pylint: disable = redefined-outer-name

import re
from unittest import mock

import pytest

pytest_plugins = ['tests.perforce_utils', 'tests.git_utils', 'tests.deployment_utils']


class FuzzyCallChecker:
    def __init__(self, mock_object):
        self.mock_object = mock_object

    def _assertion_message(self, string_to_find):
        return f"\nExpected param: {string_to_find}\nActual list: {str(self.mock_object.mock_calls)}"

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


@pytest.fixture(autouse=True)
def detect_fails(capsys, request):
    yield capsys

    out, err = capsys.readouterr()
    assert not err, f"Error detected: {err}"
    for text in ["Traceback", "Exception"]:
        assert text not in out, f"'{text}' detected in stdout!"

    if request.node.name == 'test_teardown_fixture_output_verification':
        assert out == "TearDown fixture output must be handled by 'detect_fails' fixture\n"
