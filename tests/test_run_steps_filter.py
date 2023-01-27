import pytest

from universum import __main__


config = """
from universum.configuration_support import Configuration

def step(name, cmd=False):
    return Configuration([dict(name=name, command=[] if not cmd else ["bash", "-c", '''echo "run step"'''])])

configs = step('parent 1 ') * (step('step 1', True) + step('step 2', True))
configs += step('parent 2 ') * (step('step 1', True) + step('step 2', True))
"""

empty_config = """
from universum.configuration_support import Configuration
configs = Configuration()
"""


filters_parametrize_values = (
    [["parent 1"], ["parent 1", "step 1", "step 2"], ["parent 2"]],
    [["!parent 2"], ["parent 1", "step 1", "step 2"], ["parent 2"]],
    [["parent 1:parent 2"], ["parent 1", "step 1", "step 2", "parent 2"], []],

    [["parent 1:parent 2:!step 1"], ["parent 1", "step 2", "parent 2"], ["step 1"]],
    [["step 2"], ["parent 1", "parent 2", "step 2"], ["step 1"]],
    [["!step 2:parent 1"], ["parent 1", "step 1"], ["parent 2", "step 2"]],
    [["step :!step 1"], ["parent 1", "parent 2", "step 2"], ["step 1"]],

    [[""], ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"], []],
    [["!"], ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"], []],

    [["parent 1:parent 2", "!step 1"], ["parent 1", "step 2", "parent 2"], ["step 1"]]
)

test_types = ["main", "nonci"]


@pytest.mark.parametrize("test_type", test_types)
@pytest.mark.parametrize("filters, expected_logs, unexpected_logs", filters_parametrize_values)
def test_steps_filter(tmp_path, stdout_checker, filters, expected_logs, unexpected_logs, test_type):
    params = get_cli_params(test_type, tmp_path)
    params.extend(["-o", "console"])
    for _filter in filters:
        params.append(f"-f={_filter}")
    params.extend(["-cfg", get_config_file_path(tmp_path, config)])

    return_code = __main__.main(params)

    assert return_code == 0
    for log_str in expected_logs:
        stdout_checker.assert_has_calls_with_param(log_str)
    for log_str in unexpected_logs:
        stdout_checker.assert_absent_calls_with_param(log_str)


@pytest.mark.parametrize("test_type", test_types)
def test_steps_filter_no_match(tmp_path, stdout_checker, test_type):
    include_pattern = "asdf"
    exclude_pattern = "qwer"
    cli_params = get_cli_params(test_type, tmp_path)
    cli_params.extend(["-f", f"{include_pattern}:!{exclude_pattern}"])

    check_empty_config_error(tmp_path, stdout_checker, cli_params)
    stdout_checker.assert_has_calls_with_param(include_pattern)
    stdout_checker.assert_has_calls_with_param(exclude_pattern)


@pytest.mark.parametrize("test_type", test_types)
def test_config_empty(tmp_path, stdout_checker, test_type):
    check_empty_config_error(tmp_path, stdout_checker, get_cli_params(test_type, tmp_path))


def check_empty_config_error(tmp_path, stdout_checker, cli_params):
    cli_params.extend(["-cfg", get_config_file_path(tmp_path, empty_config)])
    return_code = __main__.main(cli_params)

    assert return_code == 1
    stdout_checker.assert_has_calls_with_param("Project configs are empty")


def get_config_file_path(tmp_path, text):
    config_file = tmp_path / "configs.py"
    config_file.write_text(text, "utf-8")
    return str(config_file)


def get_cli_params(test_type, tmp_path):
    if test_type == "nonci":
        return ["nonci"]
    return ["-vt", "none",
            "-fsd", str(tmp_path),
            "--clean-build"]
