import os
import signal
import subprocess
import time
import shutil
import pathlib
from typing import Any

import pytest

from .deployment_utils import UniversumRunner, LocalSources
from .utils import python, simple_test_config


def get_line_with_text(text: str, log: str) -> str:
    for line in log.splitlines():
        if text in line:
            return line
    return ""


def test_minimal_execution(docker_main_and_nonci: UniversumRunner):
    log = docker_main_and_nonci.run(simple_test_config)
    assert docker_main_and_nonci.local.repo_file.name in log


def test_artifacts(docker_main: UniversumRunner):
    config = """
from universum.configuration_support import Configuration

mkdir = Configuration([dict(name="Create directory", command=["mkdir", "-p"])])
mkfile = Configuration([dict(name="Create file", command=["touch"])])
dirs1 = Configuration([dict(name=" one/two{}/three".format(str(x)),
                         command=["one/two{}/three".format(str(x))]) for x in range(0, 6)])
files1 = Configuration([dict(name=" one/two{}/three/file{}.txt".format(str(x), str(x)),
                          command=["one/two{}/three/file{}.txt".format(str(x), str(x))])
                     for x in range(0, 6)])

dirs2 = Configuration([dict(name=" one/three", command=["one/three"])])
files2 = Configuration([dict(name=" one/three/file.sh", command=["one/three/file.sh"])])

artifacts = Configuration([dict(name="Existing artifacts", artifacts="one/**/file*", report_artifacts="one/*"),
                           dict(name="Missing report artifacts", report_artifacts="non_existing_file"),
                           dict(name="Missing all artifacts", artifacts="something", report_artifacts="something_else")])

configs = mkdir * dirs1 + mkdir * dirs2 + mkfile * files1 + mkfile * files2 + artifacts
    """
    log = docker_main.run(config)
    assert 'Failed' in get_line_with_text("Collecting artifacts for the 'Missing all artifacts' step - ", log)
    assert 'Success' in get_line_with_text("Collecting artifacts for the 'Missing report artifacts' step - ", log)

    assert os.path.exists(os.path.join(docker_main.artifact_dir, "three.zip"))
    assert os.path.exists(os.path.join(docker_main.artifact_dir, "two2.zip"))
    assert os.path.exists(os.path.join(docker_main.artifact_dir, "file1.txt"))
    assert os.path.exists(os.path.join(docker_main.artifact_dir, "file.sh"))


def test_background_steps(docker_main_and_nonci: UniversumRunner):
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

background = Configuration([dict(name="Background", background=True)])
sleep = Configuration([dict(name=' long step', command=["sleep", "1"])])
multiply = Configuration([dict(name="_1"), dict(name="_2"), dict(name="_3")])
wait = Configuration([dict(name='Step requiring background results',
                      command=["echo", "test passed"], finish_background=True)])

script = Configuration([dict(name=" unsuccessful step", command=["ls", "non-existent-file"])])

configs = background * (script + sleep * multiply) + wait + background * (sleep + script)
""")
    assert "All ongoing background steps should be finished before next step execution" in log
    assert 'Failed' in get_line_with_text("Background unsuccessful step - ", log)

    # Test background after failed foreground (regression)
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Bad step", command=["ls", "not_a_file"]),
                         dict(name="Good bg step", command=["touch", "file"],
                         background=True, artifacts="file")])
""")
    assert "All ongoing background steps completed" in log
    assert os.path.exists(os.path.join(docker_main_and_nonci.artifact_dir, "file"))

    # Test TC step failing
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Bad bg step", command=["ls", "not_a_file"], background=True)])
""", additional_parameters=" -ot tc")
    assert "##teamcity[buildProblem description" in log

    # Test multiple failing background steps
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Bad step 1", command=["ls", "not_a_file"], background=True),
                         dict(name="Bad step 2", command=["ls", "not_a_file"], background=True)])
""")
    assert 'Failed' in get_line_with_text("Bad step 2 - ", log)


def test_critical_steps(docker_main_and_nonci: UniversumRunner):
    # Test linear
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Good step", command=["echo", "step succeeded"]),
                         dict(name="Bad step", command=["ls", "not_a_file"], critical=True),
                         dict(name="Extra step", command=["echo", "This shouldn't be in log."])])
""")
    assert "'Extra step' skipped because of critical step failure" in log
    assert "This shouldn't be in log." not in log

    # Test embedded: critical step, critical substep
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

upper = Configuration([dict(name="Group 1"),
                       dict(name="Group 2", critical=True),
                       dict(name="Group 3")])

lower = Configuration([dict(name=", step 1", command=["echo", "step succeeded"]),
                       dict(name=", step 2", command=["ls", "not_a_file"], critical=True),
                       dict(name=", step 3", command=["echo", "This shouldn't be in log."])])

configs = upper * lower
""")
    assert "'Group 3, step 1' skipped because of critical step failure" in log
    assert "'Group 2, step 1' skipped because of critical step failure" not in log

    # Test embedded: critical step, non-critical substep
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

upper = Configuration([dict(name="Group 1", critical=True),
                       dict(name="Group 2")])

lower = Configuration([dict(name=", step 1", command=["echo", "step succeeded"]),
                       dict(name=", step 2", command=["ls", "not_a_file"]),
                       dict(name=", step 3", command=["echo", "This should be in log."])])

configs = upper * lower
""")
    assert "'Group 2, step 1' skipped because of critical step failure" in log
    assert "This should be in log." in log

    # Test critical non-commands
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Group 1")])

configs *= Configuration([dict(name=", step 1", command=["echo", "step succeeded"]),
                          dict(name=", step 2", command=["this-is-not-a-command"], critical=True),
                          dict(name=", step 3", command=["echo", "This shouldn't be in log."])])

configs += Configuration([dict(name="Linear non-command", command=["this-is-not-a-command"], critical=True),
                          dict(name="Extra step", command=["echo", "This shouldn't be in log."])])
""")
    assert "This shouldn't be in log." not in log

    # Test successful critical step after failing non-critical step
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Group 1")])

configs *= Configuration([dict(name=", step 1", command=["echo", "step succeeded"]),
                          dict(name=", step 2", command=["this-is-not-a-command"]),
                          dict(name=", step 3", command=["echo", "This should be in log 1."], critical=True),
                          dict(name=", step 4", command=["echo", "This should be in log 2."])])
    """)
    assert "This should be in log 1." in log
    assert "This should be in log 2." in log

    # Test background
    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

group = Configuration([dict(name="Group")])

subgroup1 = Configuration([dict(name=" 1, step 1", command=["ls", "not_a_file"], background=True),
                           dict(name=" 1, step 2", command=["echo", "This should be in log - 1"],
                             finish_background=True)])

subgroup2 = Configuration([dict(name=" 2, step 1", command=["ls", "not_a_file"], critical=True,
                                background=True),
                           dict(name=" 2, step 2", command=["echo", "This should be in log - 2"])])

subgroup3 = Configuration([dict(name=" 3, step 1", command=["echo", "This shouldn't be in log."],
                                finish_background=True),
                           dict(name=" 3, step 2", command=["echo", "This shouldn't be in log."])])

configs = group * subgroup1 + group * subgroup2 + group * subgroup3
configs += Configuration([dict(name="Additional step", command=["echo", "This should be in log - 3"])])
""")
    assert "This shouldn't be in log." not in log
    assert "This should be in log - 1" in log
    assert "This should be in log - 2" in log
    assert "This should be in log - 3" in log


def test_empty_steps(docker_main_and_nonci: UniversumRunner):
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration, Step

configs = Configuration([Step(name="Step one"),
                         Step(name="Step two", critical=True),
                         Step(name="Step three", background=True)])
""")
    assert "'RunningStep' object has no attribute 'process'" not in log
    assert "Nothing was executed: this background step had no command" in log


def test_minimal_git(docker_main_with_vcs: UniversumRunner):
    log = docker_main_with_vcs.run(simple_test_config, vcs_type="git")
    assert docker_main_with_vcs.git.repo_file.name in log


def test_minimal_p4(docker_main_with_vcs: UniversumRunner):
    log = docker_main_with_vcs.run(simple_test_config, vcs_type="p4")
    assert docker_main_with_vcs.perforce.repo_file.name in log


def test_p4_params(docker_main_with_vcs: UniversumRunner):
    p4 = docker_main_with_vcs.perforce.p4
    p4_file = docker_main_with_vcs.perforce.repo_file
    config = f"""
from universum.configuration_support import Configuration, Step

configs = Configuration([Step(name="Test step", command=["cat", "{p4_file.name}"])])
"""

    # Prepare SYNC_CHANGELIST
    sync_cl = p4.run_changes("-s", "submitted", "-m1", docker_main_with_vcs.perforce.depot)[0]["change"]
    p4.run_edit(docker_main_with_vcs.perforce.depot)
    p4_file.write_text("This line shouldn't be in file.\n")
    change = p4.fetch_change()
    change["Description"] = "Rename basic config"
    p4.run_submit(change)

    # Prepare SHELVE_CHANGELIST
    p4.run_edit(docker_main_with_vcs.perforce.depot)
    p4_file.write_text("This line should be in file.\n")
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    # Do not pass params
    log = docker_main_with_vcs.run(config, vcs_type="p4")
    assert "This line shouldn't be in file." in log
    assert "This line should be in file." not in log

    # Pass params via command line
    docker_main_with_vcs.clean_artifacts()
    log = docker_main_with_vcs.run(config, vcs_type="p4",
                                   additional_parameters=" -p4h=" + sync_cl + " -p4s=" + shelve_cl)
    assert "This line shouldn't be in file." not in log
    assert "This line should be in file." in log

    # Pass params via environment variables
    docker_main_with_vcs.clean_artifacts()
    log = docker_main_with_vcs.run(config, vcs_type="p4", environment=["SYNC_CHANGELIST=" + sync_cl,
                                                                       "SHELVE_CHANGELIST_1=" + shelve_cl])
    assert "This line shouldn't be in file." not in log
    assert "This line should be in file." in log


def empty_required_params_ids(param: Any) -> str:
    if isinstance(param, bool):  # url_error_expected
        return 'negative' if param else 'positive'
    return str(param)


@pytest.mark.parametrize('url_error_expected, parameters, env', [
    [True, "", []],
    [True, " -ssu=''", []],
    [True, "", ["SWARM_SERVER="]],
    [True, " --build-only-latest -ssu=''", []],

    # negative Test cases
    [False, " -ssu=http://swarm", []],
    [False, "", ["SWARM_SERVER=http://swarm"]],
    [False, " --build-only-latest -ssu=http://swarm", []]
], ids=empty_required_params_ids)
def test_empty_required_params(docker_main_with_vcs: UniversumRunner, url_error_expected, parameters, env):
    url_error = "URL of the Swarm server is not specified"

    log = docker_main_with_vcs.run(simple_test_config, vcs_type="p4", expected_to_fail=True,
                                   additional_parameters=" --report-to-review" + parameters, environment=env)
    if url_error_expected:
        assert url_error in log
    else:
        assert url_error not in log


def test_environment(docker_main_and_nonci: UniversumRunner):
    script = docker_main_and_nonci.local.root_directory / "script.sh"
    script.write_text("""#!/bin/bash
echo ${SPECIAL_TESTING_VARIABLE}
""")
    script.chmod(0o777)

    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Test configuration", command=["script.sh"],
                              environment={"SPECIAL_TESTING_VARIABLE": "This string should be in log"})])
""")
    assert "This string should be in log" in log

    docker_main_and_nonci.clean_artifacts()
    log = docker_main_and_nonci.run("""
from universum.configuration_support import Configuration

upper = Configuration([dict(name="Test configuration",
                            environment={"SPECIAL_TESTING_VARIABLE": "This string should be in log"})])
lower = Configuration([dict(name=" 1", command=["script.sh"], environment={"OTHER_VARIABLE": "Something"}),
                       dict(name=" 2", command=["ls", "-la"])])
configs = upper * lower
""")
    assert "This string should be in log" in log


@pytest.mark.parametrize("terminate_type", [signal.SIGINT, signal.SIGTERM], ids=["interrupt", "terminate"])
def test_abort(local_sources: LocalSources, tmp_path: pathlib.Path, terminate_type):
    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Long step", command=["sleep", "10"])]) * 5
"""
    config_file = tmp_path / "configs.py"
    config_file.write_text(config)

    with subprocess.Popen([python(), "-m", "universum",
                           "-o", "console", "-st", "local", "-vt", "none",
                           "-pr", str(tmp_path / "project_root"),
                           "-ad", str(tmp_path / "artifacts"),
                           "-fsd", str(local_sources.root_directory),
                           "-cfg", str(config_file)]) as process:
        time.sleep(5)
        process.send_signal(terminate_type)
        assert process.wait(5) == 3


def test_exit_code(local_sources: LocalSources, tmp_path: pathlib.Path):
    config = """
from universum.configuration_support import Configuration

configs = Configuration([dict(name="Unsuccessful step", command=["exit", "1"])])
"""
    config_file = tmp_path / "configs.py"
    config_file.write_text(config)

    with subprocess.Popen([python(), "-m", "universum",
                           "-o", "console", "-st", "local", "-vt", "none",
                           "-pr", str(tmp_path / "project_root"),
                           "-ad", str(tmp_path / "artifacts"),
                           "-fsd", str(local_sources.root_directory),
                           "-cfg", str(config_file)]) as process:

        assert process.wait() == 0

    artifacts_dir = tmp_path / "artifacts"
    shutil.rmtree(str(artifacts_dir))
    with subprocess.Popen([python(), "-m", "universum", "--fail-unsuccessful",
                           "-o", "console", "-st", "local", "-vt", "none",
                           "-pr", str(tmp_path / "project_root"),
                           "-ad", str(tmp_path / "artifacts"),
                           "-fsd", str(local_sources.root_directory),
                           "-cfg", str(config_file)]) as process:
        assert process.wait() == 1
