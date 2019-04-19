#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def get_line_with_text(text, log):
    for line in log.splitlines():
        if text in line:
            return line
    return ""


def test_minimal_execution(universum_runner):
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
""")
    assert universum_runner.local.repo_file.basename in log


def test_artifacts(universum_runner):
    config = """
from _universum.configuration_support import Variations

mkdir = Variations([dict(name="Create directory", command=["mkdir", "-p"])])
mkfile = Variations([dict(name="Create file", command=["touch"])])
dirs1 = Variations([dict(name=" one/two{}/three".format(str(x)),
                         command=["one/two{}/three".format(str(x))]) for x in range(0, 6)])
files1 = Variations([dict(name=" one/two{}/three/file{}.txt".format(str(x), str(x)),
                          command=["one/two{}/three/file{}.txt".format(str(x), str(x))])
                     for x in range(0, 6)])

dirs2 = Variations([dict(name=" one/three", command=["one/three"])])
files2 = Variations([dict(name=" one/three/file.sh", command=["one/three/file.sh"])])

artifacts = Variations([dict(name="Existing artifacts", artifacts="one/**/file*", report_artifacts="one/*"),
                        dict(name="Missing artifacts", artifacts="something", report_artifacts="something_else")])

configs = mkdir * dirs1 + mkdir * dirs2 + mkfile * files1 + mkfile * files2 + artifacts
    """
    log = universum_runner.run(config)
    assert 'Failed' in get_line_with_text("Collecting 'something' - ", log)
    assert 'Success' in get_line_with_text("Collecting 'something_else' for report - ", log)

    assert os.path.exists(os.path.join(universum_runner.artifact_dir, "three.zip"))
    assert os.path.exists(os.path.join(universum_runner.artifact_dir, "two2.zip"))
    assert os.path.exists(os.path.join(universum_runner.artifact_dir, "file1.txt"))
    assert os.path.exists(os.path.join(universum_runner.artifact_dir, "file.sh"))


def test_background_steps(universum_runner):
    log = universum_runner.run("""
from _universum.configuration_support import Variations

background = Variations([dict(name="Background", background=True)])
sleep = Variations([dict(name=' long step', command=["sleep", "1"])])
multiply = Variations([dict(name="_1"), dict(name="_2"), dict(name="_3")])
wait = Variations([dict(name='Step requiring background results',
                        command=["echo", "test passed"], finish_background=True)])

script = Variations([dict(name=" unsuccessful step", command=["ls", "non-existent-file"])])

configs = background * (script + sleep * multiply) + wait + background * (sleep + script)
""")
    assert "All ongoing background steps should be finished before next step execution" in log
    assert 'Failed' in get_line_with_text("Background unsuccessful step - ", log)

    # Test background after failed foreground (regression)
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Bad step", command=["ls", "not_a_file"]),
                      dict(name="Good bg step", command=["touch", "file"],
                      background=True, artifacts="file")])
""")
    assert "All ongoing background steps completed" in log
    assert os.path.exists(os.path.join(universum_runner.artifact_dir, "file"))

    # Test TC step failing
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Bad bg step", command=["ls", "not_a_file"], background=True)])
""", additional_parameters=" -ot tc")
    assert "##teamcity[buildProblem description" in log

    # Test multiple failing background steps
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Bad step 1", command=["ls", "not_a_file"], background=True),
                      dict(name="Bad step 2", command=["ls", "not_a_file"], background=True)])
""")
    assert 'Failed' in get_line_with_text("Bad step 2 - ", log)


def test_critical_steps(universum_runner):
    # Test linear
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Good step", command=["echo", "step succeeded"]),
                      dict(name="Bad step", command=["ls", "not_a_file"], critical=True),
                      dict(name="Extra step", command=["echo", "This shouldn't be in log."])])
""")
    assert "Extra step skipped because of critical step failure" in log
    assert "This shouldn't be in log." not in log

    # Test embedded: critical step, critical substep
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

upper = Variations([dict(name="Group 1"),
                    dict(name="Group 2", critical=True),
                    dict(name="Group 3")])

lower = Variations([dict(name=", step 1", command=["echo", "step succeeded"]),
                    dict(name=", step 2", command=["ls", "not_a_file"], critical=True),
                    dict(name=", step 3", command=["echo", "This shouldn't be in log."])])

configs = upper * lower
""")
    assert "Group 3, step 1 skipped because of critical step failure" in log
    assert "Group 2, step 1 skipped because of critical step failure" not in log

    # Test embedded: critical step, non-critical substep
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

upper = Variations([dict(name="Group 1", critical=True),
                    dict(name="Group 2")])

lower = Variations([dict(name=", step 1", command=["echo", "step succeeded"]),
                    dict(name=", step 2", command=["ls", "not_a_file"]),
                    dict(name=", step 3", command=["echo", "This should be in log."])])

configs = upper * lower
""")
    assert "Group 2, step 1 skipped because of critical step failure" in log
    assert "This should be in log." in log

    # Test critical non-commands
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Group 1")])

configs *= Variations([dict(name=", step 1", command=["echo", "step succeeded"]),
                       dict(name=", step 2", command=["this-is-not-a-command"], critical=True),
                       dict(name=", step 3", command=["echo", "This shouldn't be in log."])])

configs += Variations([dict(name="Linear non-command", command=["this-is-not-a-command"], critical=True),
                       dict(name="Extra step", command=["echo", "This shouldn't be in log."])])
""")
    assert "This shouldn't be in log." not in log

    # Test background
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

group = Variations([dict(name="Group")])

subgroup1 = Variations([dict(name=" 1, step 1", command=["ls", "not_a_file"], background=True),
                        dict(name=" 1, step 2", command=["echo", "This should be in log - 1"],
                             finish_background=True)])

subgroup2 = Variations([dict(name=" 2, step 1", command=["ls", "not_a_file"], critical=True,
                             background=True),
                        dict(name=" 2, step 2", command=["echo", "This should be in log - 2"])])

subgroup3 = Variations([dict(name=" 3, step 1", command=["echo", "This shouldn't be in log."],
                             finish_background=True),
                        dict(name=" 3, step 2", command=["echo", "This shouldn't be in log."])])

configs = group * subgroup1 + group * subgroup2 + group * subgroup3
configs += Variations([dict(name="Additional step", command=["echo", "This should be in log - 3"])])
""")
    assert "This shouldn't be in log." not in log
    assert "This should be in log - 1" in log
    assert "This should be in log - 2" in log
    assert "This should be in log - 3" in log


def test_minimal_git(universum_runner):
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="git")
    assert universum_runner.git.repo_file.basename in log


def test_minimal_p4(universum_runner):
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
""", vcs_type="p4")
    assert universum_runner.perforce.repo_file.basename in log


def test_p4_params(universum_runner):
    p4 = universum_runner.perforce.p4
    p4_file = universum_runner.perforce.repo_file
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["cat", "{}"])])
""".format(p4_file.basename)

    # Prepare SYNC_CHANGELIST
    sync_cl = p4.run_changes("-s", "submitted", "-m1", universum_runner.perforce.depot)[0]["change"]
    p4.run_edit(universum_runner.perforce.depot)
    p4_file.write("This line shouldn't be in file.\n")
    change = p4.fetch_change()
    change["Description"] = "Rename basic config"
    p4.run_submit(change)

    # Prepare SHELVE_CHANGELIST
    p4.run_edit(universum_runner.perforce.depot)
    p4_file.write("This line should be in file.\n")
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    # Do not pass params
    log = universum_runner.run(config, vcs_type="p4")
    assert "This line shouldn't be in file." in log
    assert "This line should be in file." not in log

    # Pass params via command line

    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="p4",
                               additional_parameters=" -p4h=" + sync_cl + " -p4s=" + shelve_cl)
    assert "This line shouldn't be in file." not in log
    assert "This line should be in file." in log

    # Pass params via environment variables
    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="p4", environment=["SYNC_CHANGELIST=" + sync_cl,
                                                                   "SHELVE_CHANGELIST_1=" + shelve_cl])
    assert "This line shouldn't be in file." not in log
    assert "This line should be in file." in log


def test_empty_required_params(universum_runner):
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""

    log = universum_runner.run(config, vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review")
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(config, vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review -sre=''")
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(config, vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review",
                               environment=["SWARM_REVIEW=''"])
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(config, vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review --build-only-latest -sre=''")
    assert "Variable 'REVIEW' is not set" in log


def test_environment(universum_runner):
    script = universum_runner.local.root_directory.join("script.sh")
    script.write("""#!/bin/bash
echo ${SPECIAL_TESTING_VARIABLE}
""")
    script.chmod(0777)

    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["script.sh"],
                           environment={"SPECIAL_TESTING_VARIABLE": "This string should be in log"})])
""")
    assert "This string should be in log" in log

    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

upper = Variations([dict(name="Test configuration",
                         environment={"SPECIAL_TESTING_VARIABLE": "This string should be in log"})])
lower = Variations([dict(name=" 1", command=["script.sh"], environment={"OTHER_VARIABLE": "Something"}),
                    dict(name=" 2", command=["ls", "-la"])])
configs = upper * lower
""")
    assert "This string should be in log" in log
