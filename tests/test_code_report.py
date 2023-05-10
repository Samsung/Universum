import inspect
import os
import re
import pathlib
from typing import List

import pytest

from . import utils
from .conftest import FuzzyCallChecker
from .deployment_utils import UniversumRunner
from .utils import python, python_version


@pytest.fixture(name='runner_with_analyzers')
def fixture_runner_with_analyzers(docker_main: UniversumRunner):
    docker_main.environment.install_python_module("pylint")
    docker_main.environment.install_python_module("mypy")
    docker_main.environment.assert_successful_execution("apt install -y uncrustify clang-format")
    yield docker_main


class ConfigData:
    def __init__(self):
        self.text = "from universum.configuration_support import Configuration, Step\n"
        self.text += "configs = Configuration()\n"

    def add_cmd(self, name: str, cmd: str, step_config: str = '') -> 'ConfigData':
        step_config = ', ' + step_config if step_config else ''
        self.text +=\
            f"configs += Configuration([Step(name='{name}', command={cmd}{step_config})])\n"
        return self

    def add_analyzer(self, analyzer: str, arguments: List[str], step_config: str = '') -> 'ConfigData':
        name = f"Run {analyzer}"
        args = [f", '{arg}'" for arg in arguments]
        cmd = f"['{python()}', '-m', 'universum.analyzers.{analyzer}'{''.join(args)}]"
        step_config = ', ' + step_config if step_config else ''
        step_config = 'code_report=True' + step_config
        return self.add_cmd(name, cmd, step_config)

    def finalize(self) -> str:
        return inspect.cleandoc(self.text)


source_code_python = """
"Docstring."

s: str = "world"
print(f"Hello {s}.")
"""

source_code_c = """
int main() {
\treturn 0;
}
"""

json_report_minimal = """
[]
"""

json_report = """
[
    {
        "path": "my_path/my_file",
        "message": "Error!",
        "symbol": "testSymbol",
        "line": 1
    }
]
"""

sarif_report_minimal = """
{
  "version": "2.1.0",
  "runs": [
    {
      "tool": { "driver": { "name": "Dummy" } },
      "results": [ ]
    }
  ]
}
"""

sarif_report = """
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "Checkstyle",
          "semanticVersion": "8.43",
          "version": "8.43"
        }
      },
      "results": [
        {
          "level": "warning",
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "my_path/my_file"
                },
                "region": {
                  "startColumn": 1,
                  "startLine": 1
                }
              }
            }
          ],
          "message": {
            "text": "Error!"
          },
          "ruleId": "testRule"
        }
      ]
    }
  ]
}
"""

config_uncrustify = """
code_width = 120
input_tab_size = 2
"""

config_clang_format = """
---
AllowShortFunctionsOnASingleLine: Empty
"""

log_fail = r'Found [0-9]+ issues'
log_success = r'Issues not found'


@pytest.mark.parametrize('tested_contents, expected_success', [
    [[json_report_minimal], True],
    [[json_report], False],
    [[sarif_report_minimal], True],
    [[sarif_report], False],
    [[json_report_minimal, sarif_report_minimal], True],
    [[json_report, sarif_report], False],
    [[json_report_minimal, sarif_report], False],
    [[json_report, sarif_report_minimal], False],
], ids=[
    'json_no_issues',
    'json_issues_found',
    'sarif_no_issues',
    'sarif_issues_found',
    'both_tested_no_issues',
    'both_tested_issues_in_both',
    'both_tested_issues_in_sarif',
    'both_tested_issues_in_json',
])
def test_code_report_direct_log(runner_with_analyzers: UniversumRunner, tested_contents, expected_success):
    config = ConfigData()
    step_config = "code_report=True"
    for idx, tested_content in enumerate(tested_contents):
        prelim_report = "report_file_" + str(idx)
        full_report = "${CODE_REPORT_FILE}"
        (runner_with_analyzers.local.root_directory / prelim_report).write_text(tested_content)
        config.add_cmd("Report " + str(idx), f"[\"bash\", \"-c\", \"cat './{prelim_report}' >> '{full_report}'\"]",
                       step_config)
    log = runner_with_analyzers.run(config.finalize())
    expected_log = log_success if expected_success else log_fail
    assert re.findall(expected_log, log), f"'{expected_log}' is not found in '{log}'"


@pytest.mark.parametrize('analyzers, extra_args, tested_content, expected_success', [
    [['uncrustify'], [], source_code_c, True],
    [['uncrustify'], [], source_code_c.replace('\t', ' '), False],    # by default uncrustify converts spaces to tabs
    [['clang_format'], [], source_code_c.replace('\t', '  '), True],  # by default clang-format expands tabs to 2 spaces
    [['clang_format'], [], source_code_c.replace('\t', ' '), False],
    [['clang_format', 'uncrustify'], [], source_code_c.replace('\t', ' '), False],
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python, True],
    [['pylint'], ["--python-version", python_version()], source_code_python + '\n', False],
    [['mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int'), False],
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int') + '\n', False],
    # TODO: add test with rcfile
    # TODO: parametrize test for different versions of python
], ids=[
    'uncrustify_no_issues',
    'uncrustify_found_issues',
    'clang_format_no_issues',
    'clang_format_found_issues',
    'clang_format_and_uncrustify_found_issues',
    'pylint_and_mypy_both_no_issues',
    'pylint_found_issues',
    'mypy_found_issues',
    'pylint_and_mypy_found_issues_independently',
])
def test_code_report_log(runner_with_analyzers: UniversumRunner, analyzers, extra_args, tested_content, expected_success):
    common_args = [
        "--result-file", "${CODE_REPORT_FILE}",
        "--files", "source_file",
    ]
    (runner_with_analyzers.local.root_directory / "source_file").write_text(tested_content)
    config = ConfigData()
    for analyzer in analyzers:
        args = common_args + extra_args
        if analyzer == 'uncrustify':
            args += ["--cfg-file", "cfg"]
            (runner_with_analyzers.local.root_directory / "cfg").write_text(config_uncrustify)
        elif analyzer == 'clang_format':
            (runner_with_analyzers.local.root_directory / ".clang-format").write_text(config_clang_format)

        config.add_analyzer(analyzer, args)

    log = runner_with_analyzers.run(config.finalize())
    expected_log = log_success if expected_success else log_fail
    assert re.findall(expected_log, log), f"'{expected_log}' is not found in '{log}'"
    if not expected_success:
        for analyzer in analyzers:  # confirm that all analyzers fail independently
            assert re.findall(fr'Run {analyzer} - [^\n]*Failed', log), f"'{analyzer}' info is not found in '{log}'"


def test_without_code_report_command(runner_with_analyzers: UniversumRunner):
    log = runner_with_analyzers.run(utils.simple_test_config)
    pattern = re.compile(f"({log_fail}|{log_success})")
    assert not pattern.findall(log)


@pytest.mark.parametrize('analyzer', ['pylint', 'mypy', 'uncrustify', 'clang_format'])
@pytest.mark.parametrize('arg_set, expected_log', [
    [["--files", "source_file.py"], "error: the following arguments are required: --result-file"],
    [["--files", "source_file.py", "--result-file"], "result-file: expected one argument"],
    [["--result-file", "${CODE_REPORT_FILE}"], "error: the following arguments are required: --files"],
    [["--files", "--result-file", "${CODE_REPORT_FILE}"], "files: expected at least one argument"],
])
def test_analyzer_common_params(runner_with_analyzers: UniversumRunner, analyzer, arg_set, expected_log):
    test_analyzer_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log)


@pytest.mark.parametrize('analyzer', ['pylint', 'mypy'])
@pytest.mark.parametrize('arg_set, expected_log', [
    [["--python-version", "--files", "source_file.py", "--result-file", "${CODE_REPORT_FILE}"],
     "python-version: expected one argument"],
])
def test_analyzer_python_version_params(runner_with_analyzers: UniversumRunner, analyzer, arg_set, expected_log):
    test_analyzer_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log)


@pytest.mark.parametrize('analyzer, arg_set, expected_log', [
    ['pylint', ["--python-version", python_version(), "--files", "source_file",
                "--result-file", "${CODE_REPORT_FILE}", '--rcfile'],
     "rcfile: expected one argument"],
    ['uncrustify', ["--files", "source_file", "--result-file", "${CODE_REPORT_FILE}"],
     "Please specify the '--cfg-file' parameter or set 'UNCRUSTIFY_CONFIG' environment variable"],
    ['uncrustify', ["--files", "source_file", "--result-file", "${CODE_REPORT_FILE}",
                    "--cfg-file", "cfg", "--output-directory", "."],
     "Target folder must not be identical to source folder"],
    ['clang_format', ["--files", "source_file", "--result-file", "${CODE_REPORT_FILE}", "--output-directory", "."],
     "Target folder must not be identical to source folder"],
])
def test_analyzer_specific_params(runner_with_analyzers: UniversumRunner, analyzer, arg_set, expected_log):
    source_file = runner_with_analyzers.local.root_directory / "source_file"
    source_file.write_text(source_code_python)

    log = runner_with_analyzers.run(ConfigData().add_analyzer(analyzer, arg_set).finalize())
    assert re.findall(fr'Run {analyzer} - [^\n]*Failed', log), f"'{analyzer}' info is not found in '{log}'"
    assert expected_log in log, f"'{expected_log}' is not found in '{log}'"


@pytest.mark.parametrize('analyzer, extra_args, tested_content, expected_success, expected_artifact', [
    ['uncrustify', ["--report-html"], source_code_c, True, False],
    ['uncrustify', ["--report-html"], source_code_c.replace('\t', ' '), False, True],
    ['uncrustify', [], source_code_c.replace('\t', ' '), False, False],
    ['clang_format', ["--report-html"], source_code_c.replace('\t', '  '), True, False],
    ['clang_format', ["--report-html"], source_code_c, False, True],
    ['clang_format', [], source_code_c, False, False],
], ids=[
    "uncrustify_html_file_not_needed",
    "uncrustify_html_file_saved",
    "uncrustify_html_file_disabled",
    "clang_format_html_file_not_needed",
    "clang_format_html_file_saved",
    "clang_format_html_file_disabled",
])
def test_diff_html_file(runner_with_analyzers: UniversumRunner, analyzer,
                        extra_args, tested_content, expected_success, expected_artifact):

    root = runner_with_analyzers.local.root_directory
    source_file = root / "source_file"
    source_file.write_text(tested_content)
    common_args = [
        "--result-file", "${CODE_REPORT_FILE}",
        "--files", "source_file",
        "--output-directory", "diff_temp"
    ]
    if analyzer == 'uncrustify':
        (root / "cfg").write_text(config_uncrustify)
        common_args.extend(["--cfg-file", "cfg"])
    elif analyzer == 'clang_format':
        (root / ".clang-format").write_text(config_clang_format)


    args = common_args + extra_args
    extra_config = "artifacts='./diff_temp/source_file.html'"
    log = runner_with_analyzers.run(ConfigData().add_analyzer(analyzer, args, extra_config).finalize())

    expected_log = log_success if expected_success else log_fail
    assert re.findall(expected_log, log), f"'{expected_log}' is not found in '{log}'"
    expected_artifacts_state = "Success" if expected_artifact else "Failed"
    expected_log = f"Collecting artifacts for the 'Run {analyzer}' step - [^\n]*{expected_artifacts_state}"
    assert re.findall(expected_log, log), f"'{expected_log}' is not found in '{log}'"


def test_code_report_extended_arg_search(tmp_path: pathlib.Path, stdout_checker: FuzzyCallChecker):
    """
    Test if ${CODE_REPORT_FILE} is replaced not only in --result-file argument of the Step
    """
    env = utils.LocalTestEnvironment(tmp_path, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmp_path)

    source_file = tmp_path / "source_file.py"
    source_file.write_text(source_code_python + '\n')

    config = f"""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Run static pylint", code_report=True, artifacts="${{CODE_REPORT_FILE}}", command=[
    'bash', '-c', 'cd "{os.getcwd()}" && {python()} -m universum.analyzers.pylint --result-file="${{CODE_REPORT_FILE}}" \
                   --python-version {python_version()} --files {str(source_file)}'])])
"""

    env.configs_file.write_text(config)

    env.run()
    stdout_checker.assert_has_calls_with_param(log_fail, is_regexp=True)
    assert os.path.exists(os.path.join(env.settings.ArtifactCollector.artifact_dir, "Run_static_pylint.json"))


def test_code_report_extended_arg_search_embedded(tmp_path: pathlib.Path, stdout_checker: FuzzyCallChecker):
    env = utils.LocalTestEnvironment(tmp_path, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmp_path)

    source_file = tmp_path / "source_file.py"
    source_file.write_text(source_code_python + '\n')

    config = """
from universum.configuration_support import Configuration, Step

configs = Configuration([Step(critical=True)]) * Configuration([
    Step(name='This is step', command=["ls"]),
    Step(name='This is step to unfold', code_report=True, report_artifacts='${CODE_REPORT_FILE}',
         command=['bash', '-c', 'echo ${CODE_REPORT_FILE}']),
])
"""

    env.configs_file.write_text(config)

    env.run()
    stdout_checker.assert_absent_calls_with_param("${CODE_REPORT_FILE}")
