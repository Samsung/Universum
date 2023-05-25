from .deployment_utils import UniversumRunner

config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="artifact check",
                              command=["bash", "-c", '''cat {}/test_nonci.txt''']),
#                                                    ^ this helps to check artifact is deleted before launch 

                         dict(name="test_step", artifacts="test_nonci.txt",
                              command=["bash", "-c", '''echo "pwd:[$(pwd)]" && echo "test nonci" > test_nonci.txt'''])])
#                                                    ^ this helps to check the path is not changed
"""


def test_launcher_output(docker_nonci: UniversumRunner):
    """
    This test verifies that nonci mode changes the behavior of the universum by checking its output to console and log
    files. Specifically, it checks the following features of the nonci mode:
     - default output of the step is console, even when running in the terminal
     - sources are not copied to temp directory
     - artifacts are deleted before launching configs
     - version control and review system are not used
     - project root is set to current directory
    """
    cwd = str(docker_nonci.local.root_directory.absolute())
    artifacts = docker_nonci.artifact_dir
    file_output_expected = f"Adding file {artifacts}/test_step_log.txt to artifacts"
    pwd_string_in_logs = f"pwd:[{cwd}]"

    docker_nonci.environment.assert_successful_execution(
        f"bash -c 'mkdir \"{artifacts}\"; echo \"Old artifact\" > \"{artifacts}/test_nonci.txt\"'")

    docker_nonci.project_root = None  # type: ignore
    console_out_log = docker_nonci.run(config.format(artifacts), workdir=cwd)

    # the following logs are only present in the default mode of the universum
    assert file_output_expected not in console_out_log          # nonci doesn't write logs to the file by default
    assert "Reporting build start" not in console_out_log       # nonci doesn't report build start
    assert "Copying sources" not in console_out_log             # nonci doesn't copy sources
    assert "Cleaning copied sources" not in console_out_log     # nonci doesn't delete sources after work is done

    # the following logs are specific to the nonci mode of the universum
    assert "Cleaning artifacts..." in console_out_log           # nonci cleans artifacts on project launch
    assert "Old artifact" not in console_out_log                # the artifacts are actually deleted
    assert pwd_string_in_logs in console_out_log                # nonci launches step in the same directory

    # nonci doesn't require to clean artifacts between calls
    log = docker_nonci.run(config.format(artifacts), additional_parameters='-lo file', workdir=cwd)
    assert file_output_expected in log

    assert console_out_log != log
    step_log = docker_nonci.environment.assert_successful_execution(
        f"cat '{artifacts}/test_step_log.txt'")
    assert pwd_string_in_logs in step_log

    # second call of universum must not contain previous step log
    docker_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="test_step",
                              command=["bash", "-c", '''echo "Separate run"'''])])
""", additional_parameters='-lo file', workdir=cwd)

    second_run_step_log = docker_nonci.environment.assert_successful_execution(
        f"cat '{artifacts}/test_step_log.txt'")
    assert pwd_string_in_logs not in second_run_step_log
    assert "Separate run" in second_run_step_log


def test_custom_artifact_dir(docker_nonci: UniversumRunner):
    docker_nonci.run(config, additional_parameters='-ad ' + '/my/artifacts/')
    docker_nonci.environment.assert_successful_execution("test -f /my/artifacts/test_nonci.txt")
