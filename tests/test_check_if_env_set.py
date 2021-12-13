# pylint: disable = redefined-outer-name

import os
from typing import Optional
import pytest

from universum.configuration_support import Configuration
from universum.modules.launcher import check_if_env_set


@pytest.fixture(autouse=True)
def os_environ():
    env_backup = dict(os.environ)
    yield
    os.environ = env_backup


def setup_env_vars(env_vars: Optional[dict]):
    if not env_vars:
        return

    for var, val in env_vars.items():
        os.environ[var] = val


def check(if_env_set_key: str, env_vars: Optional[dict]):
    setup_env_vars(env_vars)
    if_env_set_var = Configuration([dict(if_env_set=if_env_set_key)])[0]
    return check_if_env_set(if_env_set_var)


def assert_true(if_env_set_key: str, env_vars: Optional[dict] = None):
    assert check(if_env_set_key, env_vars) is True


def assert_false(if_env_set_key: str, env_vars: Optional[dict] = None):
    assert check(if_env_set_key, env_vars) is False


##########################################################################
# if_env_set var without operator
##########################################################################

def test_if_env_set_var_without_equal_operator_no_env_var():
    assert_false("VAR")


def test_if_env_set_var_without_equal_operator_env_var_set_to_true_1():
    assert_true("VAR", {"VAR": "Y"})


def test_if_env_set_var_without_equal_operator_env_var_set_to_true_2():
    assert_true("VAR_1 && VAR_2", {"VAR_1": "True", "VAR_2": "Yes"})


def test_if_env_set_var_without_equal_operator_env_var_not_set_to_true():
    assert_false("VAR", {"VAR": "False"})


def test_if_env_set_var_without_equal_operator_one_of_env_vars_not_set_to_true_1():
    assert_false("VAR_1 && VAR_2", {"VAR_1": "True", "VAR_2": "False"})


def test_if_env_set_var_without_equal_operator_one_of_env_vars_not_set_to_true_2():
    assert_false("VAR_1 && VAR_2", {"VAR_1": "False", "VAR_2": "True"})


##########################################################################
# Equal operator
##########################################################################

def test_if_env_set_equal_operator_no_env_var():
    assert_false("VAR == some &value")


def test_if_env_set_equal_operator_right_env_var():
    assert_true("VAR == some &value", {"VAR": "some &value"})


def test_if_env_set_equal_operator_wrong_env_var():
    assert_false("VAR == some &value", {"VAR": "some"})


def test_if_env_set_equal_operator_empty_string_no_env_var():
    assert_false("VAR == ")  # var == ""


def test_if_env_set_equal_operator_and_env_var_empty_strings():
    assert_true("VAR == ", {"VAR": ""})


def test_if_env_set_equal_operator_empty_string_env_var_is_value():
    assert_false("VAR == ", {"VAR": "True"})


##########################################################################
# Not equal operator
##########################################################################

def test_if_env_set_not_equal_operator_no_env_var():
    assert_true("VAR != True")


def test_if_env_set_not_equal_operator_right_env_var():
    assert_true("VAR != True", {"VAR": "value"})


def test_if_env_set_not_equal_operator_wrong_env_var():
    assert_false("VAR != True", {"VAR": "True"})


def test_if_env_set_not_equal_operator_empty_string_no_env_var():
    assert_true("VAR != ")  # var != ""


def test_if_env_set_not_equal_operator_and_env_var_empty_strings():
    assert_false("VAR != ", {"VAR": ""})


def test_if_env_set_not_equal_operator_empty_string_env_var_is_value():
    assert_true("VAR != ", {"VAR": "True"})


##########################################################################
# Other: var naming, spaces, quotes, empty if_env_set
##########################################################################

def test_if_env_set_is_empty():
    assert_true("")


def test_if_env_set_var_name_has_not_alphanumeric_characters():
    # if var name is not correct
    assert_false("VAR_&1 == value", {"VAR_&1": "value"})


def test_if_env_set_var_name_is_digit():
    assert_false("12 == value", {"12": "value"})


def test_if_env_set_check_if_hanging_spaces_removed():
    assert_true("  VAR   ==   =value  ", {"VAR": "=value"})


def test_if_env_set_check_config_with_no_spaces():
    assert_true("VAR===value", {"VAR": "=value"})


def test_if_env_set_check_if_spaces_removed_after_value():
    assert_false("VAR == value ", {"VAR": "value "})


def test_if_env_set_quotes_and_empty_env_var_value():
    assert_false("VAR == ''", {"VAR": ""})


def test_if_env_set_quotes_and_quotes_in_env_var_value():
    assert_true("VAR == ''", {"VAR": "''"})


##########################################################################
# if_env_set not in configuration
##########################################################################

def test_if_env_set_not_in_config():
    var = Configuration([dict(code_report=True),
                         dict(artifacts="htmlcov", command=["echo 123"], pass_tag="PASS")])
    os.environ["VAR_1"] = "False"
    os.environ["VAR_2"] = ""
    for item in var:
        assert check_if_env_set(item) is True


##########################################################################
# if_env_set for multiplication
##########################################################################

def assert_equal_multiplication(expected: list, env_vars: Optional[dict] = None):
    setup_env_vars(env_vars)
    var1 = Configuration([dict(if_env_set="VAR_1 == value_1"), dict(if_env_set="VAR_2 == value_2")])
    var2 = Configuration([dict(if_env_set=" && VAR_3 == value_3")])
    configs = var1 * var2
    result = list(filter(check_if_env_set, configs.all()))
    assert expected == result


def test_multiplication_filter_no_env_vars():
    assert_equal_multiplication([])


def test_multiplication_filter_one_env_var():
    assert_equal_multiplication([], {"VAR_1": "value_1"})


def test_multiplication_filter_one_step_true():
    assert_equal_multiplication([{'if_env_set': 'VAR_2 == value_2 && VAR_3 == value_3'}],
                                {"VAR_2": "value_2", "VAR_3": "value_3"})


def test_multiplication_filter_all_true():
    assert_equal_multiplication([{'if_env_set': 'VAR_1 == value_1 && VAR_3 == value_3'},
                                 {'if_env_set': 'VAR_2 == value_2 && VAR_3 == value_3'}],
                                {"VAR_1": "value_1", "VAR_2": "value_2", "VAR_3": "value_3"})
