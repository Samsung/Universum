#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import shutil

from .perforce_utils import ignore_p4_exception


def update_directory(workspace, directory):
    workspace.p4.run_reconcile("-a", "-e", "-d", directory)
    change = workspace.p4.run_change("-o")[0]
    change["Description"] = "Update directory " + str(os.path.basename(directory))
    workspace.p4.run_submit(change)


def test_minimal_install(command_runner, perforce_workspace):
    working_dir = command_runner.get_working_directory()
    source_dir = os.path.join(working_dir, "examples")
    project_root = os.path.join(working_dir, "temp")
    artifact_dir = os.path.join(working_dir, "artifacts")

    # Install
    log = command_runner.assert_success("pip install " + working_dir)
    assert "Successfully installed" in log

    # Run without parameters
    log = command_runner.assert_failure("universum")
    assert "command not found" not in log

    # Run with parameters
    cmd = "universum --vcs-type none -fsd {} -lcp {} -pr {} -ad {}" \
        .format(source_dir, "basic_config.py", project_root, artifact_dir)
    log = command_runner.assert_success(cmd)
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/out.zip"))
    command_runner.assert_success("rm -rf {}".format(artifact_dir))

    # Run from P4
    project_dir = unicode(perforce_workspace.workspace_root.join("examples"))
    try:
        shutil.copytree(os.path.join(os.getcwd(), "examples"), project_dir)
    except OSError:
        shutil.rmtree(project_dir)
        shutil.copytree(os.path.join(os.getcwd(), "examples"), project_dir)

    ignore_p4_exception("no file(s) to reconcile", update_directory,
                        perforce_workspace, project_dir + "/...")

    cmd = "universum --p4-force-clean -p4p {} -p4u {} -p4P {} -p4d {} -p4c {} -lcp {} -pr {} -ad {}" \
        .format(perforce_workspace.p4.port,
                perforce_workspace.p4.user,
                perforce_workspace.p4.password,
                "//depot/examples/...",
                "my_disposable_p4_client",
                "basic_config.py",
                project_root,
                artifact_dir)
    log = command_runner.assert_success(cmd)
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/out.zip"))
    command_runner.assert_success("rm -rf {}".format(artifact_dir))
