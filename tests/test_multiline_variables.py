import subprocess


script = """
from universum.lib.module_arguments import ModuleArgumentParser
from universum.lib.utils import read_multiline_option

parser = ModuleArgumentParser()
# parser.add_argument('--argument', '-a', metavar='ARGUMENT')
parser.add_argument('--argument', '-a')

namespace = parser.parse_args()
print(read_multiline_option(namespace.argument))
"""


def test_success_multiline_variable(tmp_path):
    text = "This is text\nwith some line breaks\n"

    # Direct input
    script_path = tmp_path / "script.py"
    script_path.write_text(script)
    result = subprocess.run(["python3.7", script_path, "-a", text], capture_output=True, text=True)
    assert result.stdout[:-1] == text

    # File
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    result = subprocess.run(["python3.7", script_path, "-a", '@' + str(var_path)], capture_output=True, text=True)
    assert result.stdout[:-1] == text

    # Stdin
    result = subprocess.run(["python3.7", script_path, "-a", '-'], capture_output=True, text=True, input=text)
    assert result.stdout[:-1] == text
