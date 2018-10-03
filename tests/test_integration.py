#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def test_minimal_execution(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_minimal_git(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py", vcs_type="git")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_minimal_p4(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py", vcs_type="p4")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))
