#!/usr/bin/env python
# -*- coding: UTF-8 -*-


def test_minimal_install(universum_runner):

    # Run without parameters
    log = universum_runner.environment.assert_unsuccessful_execution("universum")
    assert "command not found" not in log

    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""

    # Run locally
    log = universum_runner.run(config, force_installed=True)
    assert universum_runner.local.repo_file.basename in log

    # Run from Git
    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="git", force_installed=True)
    assert universum_runner.git.repo_file.basename in log

    # Run from P4
    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="p4", force_installed=True)
    assert universum_runner.perforce.repo_file.basename in log


def test_minimal_install_with_p4python_only(universum_runner_no_gitpython, capsys):
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""

    # Run from Git
    universum_runner_no_gitpython.run(config, vcs_type="git", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from P4
    universum_runner_no_gitpython.clean_artifacts()
    log = universum_runner_no_gitpython.run(config, vcs_type="p4", force_installed=True)
    assert universum_runner_no_gitpython.perforce.repo_file.basename in log


def test_minimal_install_plain_ubuntu(universum_runner_plain_ubuntu, capsys):
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""

    # Run locally
    log = universum_runner_plain_ubuntu.run(config, force_installed=True)
    assert universum_runner_plain_ubuntu.local.repo_file.basename in log

    # Run from P4
    universum_runner_plain_ubuntu.run(config, vcs_type="p4", force_installed=True, expected_to_fail=True)
    assert "Please refer to `Prerequisites` chapter of project documentation" in capsys.readouterr().out

    # Run from Git
    universum_runner_plain_ubuntu.clean_artifacts()
    universum_runner_plain_ubuntu.environment.assert_successful_execution("apt-get install -y git")
    universum_runner_plain_ubuntu.environment.install_python_module("gitpython")
    log = universum_runner_plain_ubuntu.run(config, vcs_type="git", force_installed=True)
    assert universum_runner_plain_ubuntu.git.repo_file.basename in log
