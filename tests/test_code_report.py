import inspect
import os
import re
from typing import List

import pytest

from universum import __main__
from . import utils
from .utils import python, python_version


@pytest.fixture(name='runner_with_analyzers')
def fixture_runner_with_analyzers(docker_main):
    docker_main.environment.install_python_module("pylint")
    docker_main.environment.install_python_module("mypy")
    yield docker_main


class ConfigData:
    def __init__(self):
        self.text = "from universum.configuration_support import Configuration, Step\n"
        self.text += "configs = Configuration()\n"

    def add_analyzer(self, analyzer: str, arguments: List[str]) -> 'ConfigData':
        args = [f", '{arg}'" for arg in arguments]
        cmd = f"['{python()}', '-m', 'universum.analyzers.{analyzer}'{''.join(args)}]"
        self.text += f"configs += Configuration([Step(name='Run {analyzer}', code_report=True, command={cmd})])\n"
        return self

    def finalize(self) -> str:
        return inspect.cleandoc(self.text)


source_code_python = """
"Docstring."

s: str = "world"
print(f"Hello {s}.")
"""


log_fail = r'Found [0-9]+ issues'
log_success = r'Issues not found'


@pytest.mark.parametrize('analyzers, extra_args, tested_content, expected_success', [
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python, True],
    [['pylint'], ["--python-version", python_version()], source_code_python + '\n', False],
    [['mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int'), False],
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int') + '\n', False],
    # TODO: add test with rcfile
    # TODO: parametrize test for different versions of python
])
def test_code_report_log(runner_with_analyzers, analyzers, extra_args, tested_content, expected_success):
    common_args = [
        "--result-file", "${CODE_REPORT_FILE}",
        "--files", "source_file",
    ]
    runner_with_analyzers.local.root_directory.join("source_file").write(tested_content)
    config = ConfigData()
    for analyzer in analyzers:
        args = common_args + extra_args
        config.add_analyzer(analyzer, args)

    log = runner_with_analyzers.run(config.finalize())
    if expected_success:
        assert re.findall(log_success, log)
    else:
        assert re.findall(log_fail, log)
        for analyzer in analyzers:  # confirm that all analyzers fail independently
            assert re.findall(fr'Run {analyzer} - [^\n]*Failed', log)


def test_without_code_report_command(runner_with_analyzers):
    log = runner_with_analyzers.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run usual command", command=["ls", "-la"])])
    """)
    pattern = re.compile(f"({log_fail}|{log_success})")
    assert not pattern.findall(log)


@pytest.mark.parametrize('analyzer', ['pylint', 'mypy'])
@pytest.mark.parametrize('common_arg_set, expected_log', [
    [["--python-version", python_version(), "--files", "source_file.py", "--result-file"],
     'result-file: expected one argument'],
    [["--python-version", python_version(), "--files", "--result-file", "${CODE_REPORT_FILE}"],
     "files: expected at least one argument"],
    [["--python-version", "--files", "source_file.py", "--result-file", "${CODE_REPORT_FILE}"],
     "python-version: expected one argument"],
    [["--python-version", python_version(), "--result-file", "${CODE_REPORT_FILE}"],
     "error: the following arguments are required: --files"],
])
def test_pylint_analyzer_wrong_common_params(runner_with_analyzers, analyzer, common_arg_set, expected_log):
    test_pylint_analyzer_wrong_specific_params(runner_with_analyzers, analyzer, common_arg_set, expected_log)


@pytest.mark.parametrize('analyzer, arg_set, expected_log', [
    ['pylint', ["--python-version", python_version(), "--files", "source_file",
                "--result-file", "${CODE_REPORT_FILE}", '--rcfile'],
     "rcfile: expected one argument"],
])
def test_pylint_analyzer_wrong_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log):
    source_file = runner_with_analyzers.local.root_directory.join("source_file")
    source_file.write(source_code_python)

    log = runner_with_analyzers.run(ConfigData().add_analyzer(analyzer, arg_set).finalize())
    assert re.findall(fr'Run {analyzer} - [^\n]*Failed', log)
    assert expected_log in log


def test_code_report_extended_arg_search(tmpdir, stdout_checker):
    env = utils.TestEnvironment(tmpdir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmpdir)

    source_file = tmpdir.join("source_file.py")
    source_file.write(source_code_python + '\n')

    config = f"""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run static pylint", code_report=True, artifacts="${{CODE_REPORT_FILE}}", command=[
    'bash', '-c', 'cd "{os.getcwd()}" && {python()} -m universum.analyzers.pylint --result-file="${{CODE_REPORT_FILE}}" \
                   --python-version {python_version()} --files {str(source_file)}'])])
"""

    env.configs_file.write(config)

    res = __main__.run(env.settings)

    assert res == 0
    stdout_checker.assert_has_calls_with_param(log_fail, is_regexp=True)
    assert os.path.exists(os.path.join(env.settings.ArtifactCollector.artifact_dir, "Run_static_pylint.json"))
