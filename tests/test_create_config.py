from pathlib import Path
import subprocess


def test_create_config():
    result = subprocess.run(["python3.7", "-m", "universum", "create-config"], capture_output=True, check=True)
    new_command = ''
    for line in result.stdout.splitlines():
        if str(line).startswith('$'):
            new_command = line
    new_result = subprocess.run(new_command.split(), capture_output=True, check=True)
    Path(".universum.py").unlink()
    artifacts = Path("artifacts")
    artifacts.joinpath("CONFIGS_DUMP.txt").unlink()
    artifacts.rmdir()
    assert 'Hello world' in str(new_result.stdout)
