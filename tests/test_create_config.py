import os
import subprocess
import py

from universum import __main__
from .utils import python


empty_config = r"""
from universum.configuration_support import Configuration
configs = Configuration()
"""


def test_create_config(tmpdir: py.path.local):
    launch_parameters = dict(capture_output=True, cwd=tmpdir, env=dict(os.environ, PYTHONPATH=os.getcwd()))
    result = subprocess.run([python(), "-m", "universum", "init"], check=True, **launch_parameters)  # type: ignore
    new_command = ''
    for line in result.stdout.splitlines():
        if line.startswith(b'$ '):           # result.stdout is a byte string
            new_command = line.lstrip(b'$ ')
    new_result = subprocess.run(new_command.split(), check=True, **launch_parameters)  # type: ignore
    assert 'Hello world' in str(new_result.stdout)


def test_config_empty(tmpdir, capsys):
    config_file = tmpdir.join("configs.py")
    config_file.write_text(empty_config, "utf-8")

    cli_params = ["-vt", "none",
                  "-fsd", str(tmpdir),
                  "-cfg", str(config_file),
                  "--clean-build"]
    return_code = __main__.main(cli_params)
    assert return_code == 2
    captured = capsys.readouterr()
    assert "Project configs are empty" in captured.err
