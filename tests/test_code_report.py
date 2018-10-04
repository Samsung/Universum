#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re


def test_code_report(universum_runner):

    # Test there's no result if no pylint is installed to system
    log = universum_runner.run("config_static_issues.py")
    assert "No module named pylint" in log

    # Install pylint
    log = universum_runner.command_runner.assert_success("pip install pylint")
    assert "Successfully installed" in log

    # Test configuration with issues
    universum_runner.clean_artifacts()
    log = universum_runner.run("config_static_issues.py")
    assert "Found 11 issues" in log

    # Test configuration with no issues
    universum_runner.clean_artifacts()
    log = universum_runner.run("config_static_no_issues.py")
    assert "Issues not found." in log

    # Test configuration with no code_report
    universum_runner.clean_artifacts()
    log = universum_runner.run("basic_config.py")
    string = re.compile("(Found [0-9]+ issues|Issues not found.)")
    assert not string.findall(log)
