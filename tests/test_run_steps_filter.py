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

def get_cli_params(tmpdir):
    return ["-vt", "none",
            "-fsd", str(tmpdir),
            "--clean-build"]

nonci_cli_params = ["nonci"]


@pytest.mark.parametrize("filters, expected_logs, unexpected_logs", (
        ["parent 1", ["parent 1", "step 1", "step 2"], ["parent 2"]],
        ["!parent 2", ["parent 1", "step 1", "step 2"], ["parent 2"]],
        ["parent 1:parent 2", ["parent 1", "step 1", "step 2", "parent 2"], []],

        ["parent 1:parent 2:!step 1", ["parent 1", "step 2", "parent 2"], ["step 1"]],
        ["step 2", ["parent 1", "parent 2", "step 2"], ["step 1"]],
        ["!step 2:parent 1", ["parent 1", "step 1"], ["parent 2", "step 2"]],
        ["step :!step 1", ["parent 1", "parent 2", "step 2"], ["step 1"]],

        ["", ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"], []],
        ["!", ["parent 1", "parent 2", "parent 1 step 1", "parent 2 step 1", "parent 1 step 2", "parent 2 step 2"],
         []],))
def test_steps_filter(docker_main_and_nonci: UniversumRunner, filters, expected_logs, unexpected_logs):
    console_out_log = docker_main_and_nonci.run(config, additional_parameters=f"-o console -f='{filters}'")
    for log_str in expected_logs:
        assert log_str in console_out_log

    for log_str in unexpected_logs:
        assert log_str not in console_out_log


def test_steps_filter_few_flags(docker_main_and_nonci: UniversumRunner):
    console_out_log = docker_main_and_nonci.run(config,
                                                additional_parameters="-o console -f='parent 1:parent 2' -f='!step 1'")
    for log_str in ["parent 1", "step 2", "parent 2"]:
        assert log_str in console_out_log

    assert "step 1" not in console_out_log


def test_steps_filter_no_match(tmpdir, capsys):
    check_filter_no_match(tmpdir, capsys, get_cli_params(tmpdir))


def test_steps_filter_no_match_nonci(tmpdir, capsys):
    check_filter_no_match(tmpdir, capsys, nonci_cli_params)


def test_config_empty(tmpdir, capsys):
    check_empty_config_error(tmpdir, capsys, get_cli_params(tmpdir))


def test_config_empty_nonci(tmpdir, capsys):
    check_empty_config_error(tmpdir, capsys, nonci_cli_params)


def check_filter_no_match(tmpdir, capsys, cli_params):
    include_pattern = "asdf"
    exclude_pattern = "qwer"
    cli_params.extend(["-f", f"{include_pattern}:!{exclude_pattern}"])
    captured = check_empty_config_error(tmpdir, capsys, cli_params)
    assert include_pattern in captured.out
    assert exclude_pattern in captured.out


def check_empty_config_error(tmpdir, capsys, cli_params):
    config_file = tmpdir.join("configs.py")
    config_file.write_text(empty_config, "utf-8")

    cli_params.extend(["-cfg", str(config_file)])
    return_code = __main__.main(cli_params)
    captured = capsys.readouterr()

    assert return_code == 1
    assert "Project configs are empty" in captured.out
    assert not captured.err

    return captured
