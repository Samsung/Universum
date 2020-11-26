import os
import subprocess

from .utils import python


def test_create_config(tmpdir):
    launch_parameters = dict(capture_output=True, check=True, cwd=tmpdir, env=dict(os.environ, PYTHONPATH=os.getcwd()))
    result = subprocess.run([python(), "-m", "universum", "init"], **launch_parameters)
    new_command = ''
    for line in result.stdout.splitlines():
        if line.startswith(b'$ '):           # result.stdout is a byte string
            new_command = line.lstrip(b'$ ')
    new_result = subprocess.run(new_command.split(), **launch_parameters)
    assert 'Hello world' in str(new_result.stdout)
