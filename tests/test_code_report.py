#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re


def test_code_report(universum_runner):

    # Test there's no result if no pylint is installed to system
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run static pylint", code_report=True,
                           command=["universum_static", "--type", "pylint", "--files", "static_issues.py"])])
    """
    log = universum_runner.run(config)
    assert "No module named pylint" in log

    # Install pylint
    log = universum_runner.command_runner.assert_success("pip install pylint")
    assert "Successfully installed" in log

    # Test configuration with issues
    universum_runner.clean_artifacts()
    log = universum_runner.run(config)
    assert "Found 11 issues" in log

    # Test configuration with no issues
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run static pylint", code_report=True,
                           command=["universum_static", "--type", "pylint", "--files", "static_no_issues.py"])])
    """
    universum_runner.clean_artifacts()
    log = universum_runner.run(config)
    assert "Issues not found." in log

    # Test configuration with no code_report
    universum_runner.clean_artifacts()
    log = universum_runner.run()
    string = re.compile("(Found [0-9]+ issues|Issues not found.)")
    assert not string.findall(log)
