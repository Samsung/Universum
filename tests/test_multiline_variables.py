from universum.lib.utils import read_multiline_option
import subprocess


def test_success_multiline_variable(tmp_path):
    text = "This is text\nwith some line breaks\n"

    # Direct input
    assert read_multiline_option(text) == text

    # File
    var_path = tmp_path / "variable.txt"
    var_path.write_text(text)
    assert read_multiline_option(f"@{str(var_path)}") == text

    # Stdin
    script_path = tmp_path / "script.py"
    script_path.write_text("""
from universum.lib.module_arguments import ModuleArgumentParser
from universum.lib.utils import read_multiline_option

parser = ModuleArgumentParser()
parser.add_argument('--argument', '-a', metavar='ARGUMENT')

namespace = parser.parse_args()
print(read_multiline_option(namespace.argument))
    """)
    result = subprocess.run(["python3.7", script_path, "-a", "-"], capture_output=True, text=True, input=text)
    assert result.stdout[:-1] == text
