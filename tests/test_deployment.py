#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def test_minimal_install(universum_runner):

    # Run without parameters
    log = universum_runner.command_runner.assert_failure("universum")
    assert "command not found" not in log

    # Run with parameters
    log = universum_runner.run("basic_config.py", force_installed=True)
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))

    # Run from Git
    universum_runner.clean_artifacts()
    log = universum_runner.run("basic_config.py", vcs_type="git", force_installed=True)
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))

    # Run from P4
    universum_runner.clean_artifacts()
    log = universum_runner.run("basic_config.py", vcs_type="p4", force_installed=True)
    assert "Build for platform B 32 bits" in log

    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))
