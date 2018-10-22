#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os


def test_minimal_install(universum_runner):

    # Run without parameters
    log = universum_runner.command_runner.assert_failure("universum")
    assert "command not found" not in log

    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Test configuration", command=["ls", "-la"])])
"""

    # Run locally
    log = universum_runner.run(config, force_installed=True)
    assert universum_runner.local_file in log

    # Run from Git
    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="git", force_installed=True)
    assert universum_runner.git.repo_file.basename in log

    # Run from P4
    universum_runner.clean_artifacts()
    log = universum_runner.run(config, vcs_type="p4", force_installed=True)
    assert universum_runner.perforce.repo_file.basename in log
