# pylint: disable = redefined-outer-name

import os
import subprocess

import pytest


from universum.lib.utils import read_and_check_multiline_option
from universum.lib.module_arguments import ModuleArgumentParser, IncorrectParameterError

text = "This is text\nwith some line breaks\n"
error_message = "This is some missing argument error message"

script = f"""
from universum.lib.module_arguments import ModuleArgumentParser
from universum.lib.utils import read_and_check_multiline_option

parser = ModuleArgumentParser()
parser.add_argument('--argument', '-a', metavar='ARGUMENT')

namespace = parser.parse_args()
print(read_and_check_multiline_option(namespace, 'argument', "{error_message}"))
"""


@pytest.fixture()
def parser():
    parser = ModuleArgumentParser()
    parser.add_argument('--argument', '-a', metavar='ARGUMENT')
    yield parser


def test_success_multiline_variable(parser):
    settings = parser.parse_args(['-a', text])
    assert read_and_check_multiline_option(settings, 'argument', error_message) == text


def test_multiline_variable_files(tmp_path, parser):
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    settings = parser.parse_args(['-a', f"@{str(var_path)}"])
    assert read_and_check_multiline_option(settings, 'argument', error_message) == text

    settings = parser.parse_args(['-a', "@this-is-not-a-file"])
    with pytest.raises(IncorrectParameterError) as error:
        read_and_check_multiline_option(settings, 'argument', error_message)
    assert "argument" in str(error)
    assert "this-is-not-a-file" in str(error)


def test_multiline_variable_stdin(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text(script)
    result = subprocess.run(["python3.7", script_path, "-a", "-"], capture_output=True, text=True, input=text, check=True)
    assert result.stdout[:-1] == text

    os.environ['ARGUMENT'] = '-'
    result = subprocess.run(["python3.7", script_path], capture_output=True, text=True, input=text, env=os.environ, check=True)
    assert result.stdout[:-1] == text
    del os.environ['ARGUMENT']

    result = subprocess.run(["python3.7", script_path, "-a", "-"], capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "IncorrectParameterError" in result.stderr
    assert error_message in result.stderr
