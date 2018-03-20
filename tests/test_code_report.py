#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re


def test_code_report(command_runner, universum_runner):

    log = universum_runner.run_from_source("config_static_issues.py")
    assert "No module named pylint" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/Run_static_pylint_log.txt"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))

    log = command_runner.assert_success("pip install pylint")
    assert "Successfully installed" in log

    log = universum_runner.run_from_source("config_static_issues.py")
    assert "Found 11 issues" in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/Run_static_pylint_log.txt"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))

    log = universum_runner.run_from_source("config_static_no_issues.py")
    assert "Issues not found." in log

    assert os.path.exists(os.path.join(os.getcwd(), "artifacts/Run_static_pylint_log.txt"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))

    log = universum_runner.run_from_source("basic_config.py")
    string = re.compile("(Found [0-9]+ issues|Issues not found.)")
    assert not string.findall(log)

    assert not os.path.exists(os.path.join(os.getcwd(), "artifacts/Run_static_pylint_log.txt"))
    command_runner.assert_success("rm -rf {}".format(universum_runner.artifact_dir))
