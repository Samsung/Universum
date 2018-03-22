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


def test_minimal_install(command_runner, perforce_workspace, universum_runner):

    # Run without parameters
    log = command_runner.assert_failure("universum")
    assert "command not found" not in log

    # Run with parameters
    log = universum_runner.run_from_source("basic_config.py")
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/out.zip"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))

    # Run from P4
    project_dir = unicode(perforce_workspace.root_directory.join("examples"))
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
                universum_runner.project_root,
                universum_runner.artifact_dir)
    log = command_runner.assert_success(cmd)
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/out.zip"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))
