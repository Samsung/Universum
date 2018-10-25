#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re


def test_code_report(universum_runner):
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run static pylint", code_report=True,
                           command=["universum_pylint", "--python-version=2", "--files", "source_file.py",
                           "--result-file", "${CODE_REPORT_FILE}"])])
"""

    source_code = """
"Docstring."

print "Hello world."
"""

    universum_runner.environment.install_python_module("pylint")
    source_file = universum_runner.local.root_directory.join("source_file.py")

    # Test configuration with issues
    universum_runner.clean_artifacts()
    source_file.write(source_code + "\n")
    log = universum_runner.run(config)
    assert "Found 1 issues" in log

    # Test configuration with no issues
    universum_runner.clean_artifacts()
    source_file.write(source_code)
    log = universum_runner.run(config)
    assert "Issues not found." in log

    # Test configuration with no code_report
    universum_runner.clean_artifacts()
    log = universum_runner.run("""
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run usual command", command=["ls", "-la"])])
    """)
    string = re.compile("(Found [0-9]+ issues|Issues not found.)")
    assert not string.findall(log)
