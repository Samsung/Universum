#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re


def test_code_report(universum_runner):
    config = """
from _universum.configuration_support import Variations

configs = Variations([dict(name="Run static pylint", code_report=True,
                           command=["universum_static", "--type", "pylint", "--files", "source_file.py"])])
"""

    source_code = """
"Docstring."

print "Hello world."
"""

    # Install pylint
    log = universum_runner.command_runner.assert_success("pip install pylint")
    assert "Successfully installed" in log

    # Test configuration with issues
    source_file = os.path.join(universum_runner.local_sources, "source_file.py")
    with open(source_file, 'wb+') as f:
        f.write(source_code + "\n")
        f.close()
    universum_runner.clean_artifacts()
    log = universum_runner.run(config)
    assert "Found 1 issues" in log

    # Test configuration with no issues
    source_file = os.path.join(universum_runner.local_sources, "source_file.py")
    with open(source_file, 'wb+') as f:
        f.write(source_code)
        f.close()
    universum_runner.clean_artifacts()
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
