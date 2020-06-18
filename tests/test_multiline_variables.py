import os
import pytest
import subprocess

from universum.lib.utils import read_multiline_option
from universum.lib.module_arguments import IncorrectParameterError

text = "This is text\nwith some line breaks\n"

script = """
from universum.lib.module_arguments import ModuleArgumentParser
from universum.lib.utils import read_multiline_option

parser = ModuleArgumentParser()
parser.add_argument('--argument', '-a', metavar='ARGUMENT')

namespace = parser.parse_args()
print(read_multiline_option(namespace.argument))
"""


def test_success_multiline_variable():
    assert read_multiline_option(text) == text


def test_multiline_variable_files(tmp_path):
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    assert read_multiline_option(f"@{str(var_path)}") == text

    with pytest.raises(IncorrectParameterError) as error:
        read_multiline_option(f"@this-is-not-a-file")
    assert "[Errno 2] No such file or directory" in str(error)


def test_multiline_variable_stdin(tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text(script)
    result = subprocess.run(["python3.7", script_path, "-a", "-"], capture_output=True, text=True, input=text)
    assert result.stdout[:-1] == text

    result = subprocess.run(["python3.7", script_path, "-a", "-"], capture_output=True, text=True)
    assert result.stdout == "\n"

    os.environ['ARGUMENT'] = '-'
    result = subprocess.run(["python3.7", script_path], capture_output=True, text=True, input=text)
    assert result.stdout[:-1] == text
    del os.environ['ARGUMENT']
