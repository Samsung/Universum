# pylint: disable = redefined-outer-name

import os
import subprocess

from universum.lib.gravity import construct_component
from universum.lib.module_arguments import ModuleArgumentParser
from universum.modules.error_state import HasErrorState
from .utils import PYTHON_VERSION

text = "This is text\nwith some line breaks\n"
error_message = "This is some missing argument error message"

script = f"""
from universum.lib.module_arguments import ModuleArgumentParser
from universum.lib.gravity import construct_component
from universum.modules.error_state import HasErrorState

parser = ModuleArgumentParser()
parser.add_argument('--argument', '-a', dest='HasErrorState.argument', metavar='ARGUMENT')

namespace = parser.parse_args()
module = construct_component(HasErrorState, namespace)
print(module.read_and_check_multiline_option('argument', "{error_message}"))
if module.is_in_error_state():
    print(module.global_error_state.get_errors()[0])
"""


def construct_test_module(args):
    argument_parser = ModuleArgumentParser()
    argument_parser.add_argument('--argument', '-a', dest='HasErrorState.argument', metavar='ARGUMENT')
    settings = argument_parser.parse_args(args)
    return construct_component(HasErrorState, settings)


def test_success_multiline_variable():
    module = construct_test_module(['-a', text])
    assert module.read_and_check_multiline_option('argument', error_message) == text


def test_multiline_variable_files(tmp_path):
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    module = construct_test_module(['-a', f"@{str(var_path)}"])
    assert module.read_and_check_multiline_option('argument', error_message) == text

    module = construct_test_module(['-a', "@this-is-not-a-file"])
    module.read_and_check_multiline_option('argument', error_message)
    assert module.is_in_error_state()
    error = module.global_error_state.get_errors()[0]
    assert "argument" in str(error)
    assert "this-is-not-a-file" in str(error)


def test_multiline_variable_stdin(tmp_path):
    script_file = tmp_path / "script.py"
    script_file.write_text(script)
    script_path = str(script_file)

    env = dict(os.environ)
    env['PYTHONPATH'] = os.getcwd()
    common_args = {"capture_output": True, "text": True, "env": env}

    result = subprocess.run(["python" + PYTHON_VERSION, script_path, "-a", "-"], **common_args, input=text, check=True)
    assert result.stdout[:-1] == text

    env['ARGUMENT'] = '-'
    result = subprocess.run(["python" + PYTHON_VERSION, script_path], **common_args, input=text, check=True)
    assert result.stdout[:-1] == text
    del env['ARGUMENT']

    result = subprocess.run(["python" + PYTHON_VERSION, script_path, "-a", "-"], **common_args, input="", check=False)
    assert error_message in result.stdout
