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
    docker_main.environment.assert_successful_execution("apt install uncrustify")
    yield docker_main


class ConfigData:
    def __init__(self):
        self.text = "from universum.configuration_support import Configuration, Step\n"
        self.text += "configs = Configuration()\n"

    def add_analyzer(self, analyzer: str, arguments: List[str], extra_cfg: str = '') -> 'ConfigData':
        args = [f", '{arg}'" for arg in arguments]
        cmd = f"['{python()}', '-m', 'universum.analyzers.{analyzer}'{''.join(args)}]"
        self.text +=\
            f"configs += Configuration([Step(name='Run {analyzer}', {extra_cfg} code_report=True, command={cmd})])\n"
        return self

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

scan_build_html_report = """
<html><head></head><body>
<!-- REPORTHEADER -->
<h3>Bug Summary</h3>
<table class="simpletable">
<tr><td class="rowname">File:</td><td>my_path/my_file.c</td></tr>
<tr><td class="rowname">Warning:</td><td><a href="#EndPath">line 1, column 1</a><br />Error!</td></tr>
</table></body></html>
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

cfg_uncrustify = """
code_width = 120
input_tab_size = 2
"""

log_fail = r'Found [0-9]+ issues'
log_success = r'Issues not found'


@pytest.mark.parametrize('analyzers, extra_args, tested_content, expected_success', [
    [['sarif_report'], [], sarif_report_minimal, True],
    [['sarif_report'], [], sarif_report, False],
    [['scan_build_report'], [], "<html></html>", True],
    [['scan_build_report'], [], scan_build_html_report, False],
    [['uncrustify'], [], source_code_c, True],
    [['uncrustify'], [], source_code_c.replace('\t', ' '), False],
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python, True],
    [['pylint'], ["--python-version", python_version()], source_code_python + '\n', False],
    [['mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int'), False],
    [['pylint', 'mypy'], ["--python-version", python_version()], source_code_python.replace(': str', ': int') + '\n', False],
    # TODO: add test with rcfile
    # TODO: parametrize test for different versions of python
], ids=[
    'sarif_no_issues',
    'sarif_issues_found',
    'scan_build_no_issues',
    'scan_build_issues_found',
    'uncrustify_no_issues',
    'uncrustify_found_issues',
    'pylint_and_mypy_both_no_issues',
    'pylint_found_issues',
    'mypy_found_issues',
    'pylint_and_mypy_found_issues_independently',
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
        if analyzer == 'uncrustify':
            args += ["--cfg-file", "cfg"]
            runner_with_analyzers.local.root_directory.join("cfg").write(cfg_uncrustify)
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


@pytest.mark.parametrize('analyzer', ['sarif_report', 'scan_build_report', 'pylint', 'mypy', 'uncrustify'])
@pytest.mark.parametrize('arg_set, expected_log', [
    [["--files", "source_file.py"], "error: the following arguments are required: --result-file"],
    [["--files", "source_file.py", "--result-file"], "result-file: expected one argument"],
    [["--result-file", "${CODE_REPORT_FILE}"], "error: the following arguments are required: --files"],
    [["--files", "--result-file", "${CODE_REPORT_FILE}"], "files: expected at least one argument"],
])
def test_analyzer_common_params(runner_with_analyzers, analyzer, arg_set, expected_log):
    test_analyzer_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log)


@pytest.mark.parametrize('analyzer', ['pylint', 'mypy'])
@pytest.mark.parametrize('arg_set, expected_log', [
    [["--python-version", "--files", "source_file.py", "--result-file", "${CODE_REPORT_FILE}"],
     "python-version: expected one argument"],
])
def test_analyzer_python_version_params(runner_with_analyzers, analyzer, arg_set, expected_log):
    test_analyzer_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log)


@pytest.mark.parametrize('analyzer, arg_set, expected_log', [
    ['pylint', ["--python-version", python_version(), "--files", "source_file",
                "--result-file", "${CODE_REPORT_FILE}", '--rcfile'],
     "rcfile: expected one argument"],
    ['uncrustify', ["--files", "source_file", "--result-file", "${CODE_REPORT_FILE}"],
     "Please specify the '--cfg_file' parameter or set an env. variable 'UNCRUSTIFY_CONFIG'"],
    ['uncrustify', ["--files", "source_file", "--result-file", "${CODE_REPORT_FILE}",
                    "--cfg-file", "cfg", "--output-directory", "."],
     "Target and source folders for uncrustify are not allowed to match"],
])
def test_analyzer_specific_params(runner_with_analyzers, analyzer, arg_set, expected_log):
    source_file = runner_with_analyzers.local.root_directory.join("source_file")
    source_file.write(source_code_python)

    log = runner_with_analyzers.run(ConfigData().add_analyzer(analyzer, arg_set).finalize())
    assert re.findall(fr'Run {analyzer} - [^\n]*Failed', log)
    assert expected_log in log


@pytest.mark.parametrize('extra_args, tested_content, expected_success, expected_artifact', [
    [[], source_code_c, True, False],
    [["--report-html"], source_code_c.replace('\t', ' '), False, True],
    [[], source_code_c.replace('\t', ' '), False, False],
], ids=[
    "uncrustify_html_file_not_needed",
    "uncrustify_html_file_saved",
    "uncrustify_html_file_disabled",
])
def test_uncrustify_file_diff(runner_with_analyzers, extra_args, tested_content, expected_success, expected_artifact):
    root = runner_with_analyzers.local.root_directory
    source_file = root.join("source_file")
    source_file.write(tested_content)
    root.join("cfg").write(cfg_uncrustify)
    common_args = [
        "--result-file", "${CODE_REPORT_FILE}",
        "--files", "source_file",
        "--cfg-file", "cfg",
    ]

    args = common_args + extra_args
    extra_cfg = "artifacts='./uncrustify/source_file.html',"
    log = runner_with_analyzers.run(ConfigData().add_analyzer('uncrustify', args, extra_cfg).finalize())

    assert re.findall(log_success if expected_success else log_fail, log)
    assert re.findall(r"Collecting 'source_file.html' - [^\n]*Success" if expected_artifact
                      else r"Collecting 'source_file.html' - [^\n]*Failed", log)


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


def test_code_report_extended_arg_search_embedded(tmpdir, stdout_checker):
    env = utils.TestEnvironment(tmpdir, "main")
    env.settings.Vcs.type = "none"
    env.settings.LocalMainVcs.source_dir = str(tmpdir)

    source_file = tmpdir.join("source_file.py")
    source_file.write(source_code_python + '\n')

    config = """
from universum.configuration_support import Configuration, Step

configs = Configuration([Step(critical=True)]) * Configuration([
    Step(name='This is step', command=["ls"]),
    Step(name='This is step to unfold', code_report=True, report_artifacts='${CODE_REPORT_FILE}',
         command=['bash', '-c', 'echo ${CODE_REPORT_FILE}']),
])
"""

    env.configs_file.write(config)

    res = __main__.run(env.settings)

    assert res == 0
    stdout_checker.assert_absent_calls_with_param("${CODE_REPORT_FILE}")
