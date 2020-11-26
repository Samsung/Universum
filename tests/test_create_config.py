from pathlib import Path
import os
import subprocess

from .utils import python


def test_create_config(tmpdir):
    test_environment = dict(os.environ, PYTHONPATH=os.getcwd())
    result = subprocess.run([python(), "-m", "universum", "init"],
                            capture_output=True, check=True, cwd=tmpdir, env=test_environment)
    new_command = ''
    for line in result.stdout.splitlines():
        if line.startswith(b'$ '):           # result.stdout is a byte string
            new_command = line.lstrip(b'$ ')
    new_result = subprocess.run(new_command.split(), capture_output=True, check=True, cwd=tmpdir, env=test_environment)
    Path(tmpdir, ".universum.py").unlink()
    artifacts = Path(tmpdir, "artifacts")
    artifacts.joinpath("CONFIGS_DUMP.txt").unlink()
    artifacts.rmdir()
    assert 'Hello world' in str(new_result.stdout)
