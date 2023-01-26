import os
import subprocess
import pathlib

from .utils import python


def test_create_config(tmp_path: pathlib.Path):
    launch_parameters = dict(capture_output=True, cwd=tmp_path, env=dict(os.environ, PYTHONPATH=os.getcwd()))
    result = subprocess.run([python(), "-m", "universum", "init"], check=True, **launch_parameters)  # type: ignore
    new_command = ''
    for line in result.stdout.splitlines():
        if line.startswith(b'$ '):           # result.stdout is a byte string
            new_command = line.lstrip(b'$ ')
    new_result = subprocess.run(new_command.split(), check=True, **launch_parameters)  # type: ignore
    assert 'Hello world' in str(new_result.stdout)
