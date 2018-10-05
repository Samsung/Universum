#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def test_minimal_execution(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_artifacts(universum_runner):
    log = universum_runner.run_with_coverage("configs_artifacts.py")
    assert "Collecting 'something' - Failed" in log
    assert "Collecting 'something_else' for report - Success" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "three.zip"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "two2.zip"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "file1.txt"))
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "file.sh"))


def test_background_steps(universum_runner):
    log = universum_runner.run_with_coverage("configs_background.py")
    assert "Will continue in background" in log
    assert "All ongoing background steps should be finished before execution" in log
    assert "Reported this background step as failed" in log
    assert "All ongoing background steps completed" in log


def test_critical_steps(universum_runner):
    log = universum_runner.run_with_coverage("configs_critical.py")
    assert "Critical step failed. All further configurations will be skipped" in log
    assert "skipped because of critical step failure" in log


def test_minimal_git(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py", vcs_type="git")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))


def test_minimal_p4(universum_runner):
    log = universum_runner.run_with_coverage("basic_config.py", vcs_type="p4")
    assert "Build for platform B 32 bits" in log
    assert os.path.exists(os.path.join(os.getcwd(), universum_runner.artifact_dir, "out.zip"))
