#!/usr/bin/env python
# -*- coding: UTF-8 -*-

config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""


def test_minimal_install(clean_universum_runner):
    # Run without parameters
    log = clean_universum_runner.environment.assert_unsuccessful_execution("universum")
    assert "command not found" not in log

    # Run locally
    log = clean_universum_runner.run(config, force_installed=True)
    assert clean_universum_runner.local.repo_file.basename in log

    # Run from Git
    clean_universum_runner.clean_artifacts()
    log = clean_universum_runner.run(config, vcs_type="git", force_installed=True)
    assert clean_universum_runner.git.repo_file.basename in log

    # Run from P4
    clean_universum_runner.clean_artifacts()
    log = clean_universum_runner.run(config, vcs_type="p4", force_installed=True)
    assert clean_universum_runner.perforce.repo_file.basename in log


def test_minimal_install_with_git_only(clean_universum_runner_no_p4, capsys):
    # Run from P4
    clean_universum_runner_no_p4.run(config, vcs_type="p4", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from git
    clean_universum_runner_no_p4.clean_artifacts()
    log = clean_universum_runner_no_p4.run(config, vcs_type="git", force_installed=True)
    assert clean_universum_runner_no_p4.git.repo_file.basename in log


def test_minimal_install_plain_ubuntu(clean_universum_runner_no_vcs, capsys):
    # Run from P4
    clean_universum_runner_no_vcs.run(config, vcs_type="p4", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from Git
    clean_universum_runner_no_vcs.run(config, vcs_type="git", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run locally
    log = clean_universum_runner_no_vcs.run(config, force_installed=True)
    assert clean_universum_runner_no_vcs.local.repo_file.basename in log
