#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def test_minimal_execution(universum_runner):
    log = universum_runner.run()
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


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
    assert "Collecting 'something' - Failed" in log
    assert "Collecting 'something_else' for report - Success" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "three.zip"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "two2.zip"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "file1.txt"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "file.sh"))


def test_background_steps(universum_runner):
    config = """
from _universum.configuration_support import Variations

background = Variations([dict(name="Background", background=True)])
sleep = Variations([dict(name=' long step', command=["sleep", "1"])])
multiply = Variations([dict(name="_1"), dict(name="_2"), dict(name="_3")])
wait = Variations([dict(name='Step requiring background results',
                        command=["run.sh", "pass"], finish_background=True)])

script = Variations([dict(name=" unsuccessful step", command=["run.sh", "fail"])])

configs = background * (script + sleep * multiply) + wait + background * (sleep + script)
    """
    log = universum_runner.run(config)
    assert "Will continue in background" in log
    assert "All ongoing background steps should be finished before execution" in log
    assert "Reported this background step as failed" in log
    assert "All ongoing background steps completed" in log


def test_critical_steps(universum_runner):
    config = """
from _universum.configuration_support import Variations

not_script = Variations([dict(name='Not script', command=["not_run.sh"], critical=True)])

script = Variations([dict(command=["run.sh"])])

step = Variations([dict(name='Step 1', critical=True), dict(name='Step 2')])

substep = Variations([dict(name=', failed substep', command=["fail"]),
                      dict(name=', successful substep', command=["pass"])])

configs = script * step * substep + not_script + script
    """
    log = universum_runner.run(config)
    assert "Critical step failed. All further configurations will be skipped" in log
    assert "skipped because of critical step failure" in log


def test_minimal_git(universum_runner):
    log = universum_runner.run(vcs_type="git")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_minimal_p4(universum_runner):
    log = universum_runner.run(vcs_type="p4")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_p4_params(universum_runner):
    p4 = universum_runner.perforce_workspace.p4

    # Make repository unbuildible
    p4.run_edit(universum_runner.p4_path)
    p4.run_move("//depot/examples/basic_build_script.sh", "//depot/examples/script.sh")
    change = p4.fetch_change()
    change["Description"] = "Rename build script"
    p4.run_submit(change)

    # Prepare SYNC_CHANGELIST
    sync_cl = p4.run_changes("-s", "submitted", "-m1", universum_runner.p4_path)[0]["change"]
    p4.run_edit(universum_runner.p4_path)
    p4.run_move("//depot/examples/basic_config.py", "//depot/examples/integration_config.py")
    change = p4.fetch_change()
    change["Description"] = "Rename basic config"
    p4.run_submit(change)

    # Prepare SHELVE_CHANGELIST
    p4.run_edit(universum_runner.p4_path)
    p4.run_move("//depot/examples/script.sh", "//depot/examples/basic_build_script.sh")
    change = p4.fetch_change()
    change["Description"] = "CL for shelving"
    shelve_cl = p4.save_change(change)[0].split()[1]
    p4.run_shelve("-fc", shelve_cl)

    # Do not pass params
    log = universum_runner.run(vcs_type="p4", expected_to_fail=True)
    # Parsing config should fail, return exit code 1 and print the following message with details
    assert "No such file or directory" in log

    # Pass params via command line
    universum_runner.clean_artifacts()
    log = universum_runner.run(vcs_type="p4", additional_parameters=" -p4h=" + sync_cl)
    # Every build step should fail because of missing script to run cmd
    assert "No such file or command" in log

    universum_runner.clean_artifacts()
    log = universum_runner.run(vcs_type="p4", additional_parameters=" -p4h=" + sync_cl + " -p4s=" + shelve_cl)
    assert "No such file or command" not in log

    # Pass params via environment variables
    universum_runner.clean_artifacts()
    log = universum_runner.run(vcs_type="p4", environment=["SYNC_CHANGELIST=" + sync_cl,
                                                           "SHELVE_CHANGELIST_1=" + shelve_cl])
    assert "No such file or command" not in log


def test_empty_required_params(universum_runner):
    log = universum_runner.run(vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review")
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review -sre=''")
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review",
                               environment=["SWARM_REVIEW=''"])
    assert "Variable 'REVIEW' is not set" in log

    log = universum_runner.run(vcs_type="p4", expected_to_fail=True,
                               additional_parameters=" --report-to-review --build-only-latest -sre=''")
    assert "Variable 'REVIEW' is not set" in log
