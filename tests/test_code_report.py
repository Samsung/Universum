import inspect
import os
import re
from typing import List

import pytest

from universum import __main__
from . import utils
from .utils import python, python_version


@pytest.fixture(name='runner_with_pylint')
def fixture_runner_with_pylint(docker_main_and_nonci):
    docker_main_and_nonci.environment.install_python_module("pylint")
    yield docker_main_and_nonci


def get_config(args: List[str]):
    args = [f", '{arg}'" for arg in args]
    return inspect.cleandoc(f"""
        from universum.configuration_support import Configuration

        configs = Configuration([dict(name="Run static pylint", code_report=True,
            command=['{python()}', '-m', 'universum.analyzers.pylint'{''.join(args)}])])
    """)


source_code = """
"Docstring."

print("Hello world.")
"""

log_fail = r'Found [0-9]+ issues'
log_success = r'Issues not found.'


@pytest.mark.parametrize('args, tested_content, expected_log', [
    [["--result-file", "${CODE_REPORT_FILE}"], source_code, log_success],
    [["--result-file", "${CODE_REPORT_FILE}"], source_code + '\n', log_fail]

    # TODO: add test with rcfile
    # TODO: parametrize test for different versions of python
])
def test_code_report(runner_with_pylint, args, tested_content, expected_log):
    runner_with_pylint.local.root_directory.join("source_file.py").write(tested_content)
    config = get_config(["--python-version", python_version(), "--files", "source_file.py"] + args)

    log = runner_with_pylint.run(config)
    assert re.findall(expected_log, log)


def test_without_code_report_command(runner_with_pylint):
    log = runner_with_pylint.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run usual command", command=["ls", "-la"])])
    """)
    pattern = re.compile(f"({log_fail}|{log_success})")
    assert not pattern.findall(log)


@pytest.mark.parametrize('args, expected_log', [
    [["--python-version", python_version(), "--files", "source_file.py", "--result-file", "${CODE_REPORT_FILE}", '--rcfile'],
     'rcfile: expected one argument'],
    [["--python-version", python_version(), "--files", "source_file.py", "--result-file"],
     'result-file: expected one argument'],
    [["--python-version", python_version(), "--files", "--result-file", "${CODE_REPORT_FILE}"],
     "files: expected at least one argument"],

    [["--python-version", "--files", "source_file.py", "--result-file", "${CODE_REPORT_FILE}"],
     "python-version: expected one argument"],
    [["--python-version", python_version(), "--result-file", "${CODE_REPORT_FILE}"],
     "error: the following arguments are required: --files"],
])
def test_pylint_analyzer_wrong_params(runner_with_pylint, args, expected_log):
    source_file = runner_with_pylint.local.root_directory.join("source_file.py")
    source_file.write(source_code)

    log = runner_with_pylint.run(get_config(args))
    assert re.findall(r'Run static pylint - [^\n]*Failed', log)
    assert expected_log in log


def test_code_report_extended_arg_search(tmpdir, stdout_checker):
    env = utils.TestEnvironment(tmpdir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmpdir)

    tmpdir.join("source_file.py").write(source_code + '\n')

    config = f"""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run static pylint", code_report=True, artifacts="${{CODE_REPORT_FILE}}", command=[
    'bash', '-c', 'cd "{os.getcwd()}" && {python()} -m universum.analyzers.pylint --result-file="${{CODE_REPORT_FILE}}" \
                   --python-version {python_version()} --files {str(tmpdir.join("source_file.py"))}'])])
"""

    env.configs_file.write(config)

    res = __main__.run(env.settings)

    assert res == 0
    stdout_checker.assert_has_calls_with_param(log_fail, is_regexp=True)
    assert os.path.exists(os.path.join(env.settings.ArtifactCollector.artifact_dir, "Run_static_pylint.json"))
