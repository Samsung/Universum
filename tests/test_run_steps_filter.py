import pytest

from universum import __main__
from .deployment_utils import UniversumRunner


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
def test_steps_filter(tmpdir, capsys, filters, expected_logs, unexpected_logs, test_type):
    params = get_cli_params(test_type, tmpdir)
    params.extend(["-o", "console"])
    for _filter in filters:
        params.append(f"-f={_filter}")
    params.extend(["-cfg", get_config_file_path(tmpdir, config)])

    return_code = __main__.main(params)
    captured = capsys.readouterr()

    assert return_code == 0
    for log_str in expected_logs:
        assert log_str in captured.out
    for log_str in unexpected_logs:
        assert log_str not in captured.out
    assert not captured.err


@pytest.mark.parametrize("test_type", test_types)
def test_steps_filter_no_match(tmpdir, capsys, test_type):
    include_pattern = "asdf"
    exclude_pattern = "qwer"
    cli_params = get_cli_params(test_type, tmpdir)
    cli_params.extend(["-f", f"{include_pattern}:!{exclude_pattern}"])

    captured = check_empty_config_error(tmpdir, capsys, cli_params)

    assert include_pattern in captured.out
    assert exclude_pattern in captured.out


@pytest.mark.parametrize("test_type", test_types)
def test_config_empty(tmpdir, capsys, test_type):
    check_empty_config_error(tmpdir, capsys, get_cli_params(test_type, tmpdir))


def check_empty_config_error(tmpdir, capsys, cli_params):
    cli_params.extend(["-cfg", get_config_file_path(tmpdir, empty_config)])
    return_code = __main__.main(cli_params)
    captured = capsys.readouterr()

    assert return_code == 1
    assert "Project configs are empty" in captured.out
    assert not captured.err

    return captured


def get_config_file_path(tmpdir, text):
    config_file = tmpdir.join("configs.py")
    config_file.write_text(text, "utf-8")
    return str(config_file)


def get_cli_params(test_type, tmpdir):
    if test_type == "nonci":
        return ["nonci"]
    return ["-vt", "none",
            "-fsd", str(tmpdir),
            "--clean-build"]
