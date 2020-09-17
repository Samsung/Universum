from pathlib import Path
import subprocess


def test_create_config():
    result = subprocess.run(["python3.7", "-m", "universum", "create-config"], capture_output=True, check=True)
    new_command = result.stdout.splitlines()[3]
    new_result = subprocess.run(new_command.split(), capture_output=True, check=True)
    Path("universum_config.py").unlink()
    assert 'Hello world' in str(new_result.stdout)
